import json
import re
import concurrent.futures

from textwrap import dedent
from typing import Any, Dict, List
import dspy
from loguru import logger
from pydantic import BaseModel, Field
from rich.panel import Panel
from rich.console import Console

from server.utils import LoggingLM, render


TEST_DESIGNER_PROMPT = """
You are a test scenario designer specialized in creating diverse, unique ideas for testing scenarios.
"""

TEST_CASE_CREATOR_PROMPT = """
You are a test case creator specializing in designing evaluation scenarios.
"""


class IdeaGeneration(dspy.Signature):
    # This is the system prompt for the test scenario designer
    """You are a test scenario designer specialized in creating diverse, unique ideas for testing scenarios.
        Generate unique, diverse test cases ideas for testing a prompt that accomplishes a task_description.
        Each idea should represent a distinct scenario or example that tests different aspects of the task description.

        
        Ensure each idea will be:
        - Clearly distinct from the others
        - Relevant to the task_description
        - Specific enough to guide generation of a full test case
        - Quick to solve without requiring extensive computation or multi-step processing
        - Solvable with no more than 400 tokens of output

        Remember, only generate the number of test cases for unique ideas specified in the input.
    """    
    
    num_test_cases: int = dspy.InputField(desc="The number of test cases to generate")
    task_description: str = dspy.InputField(desc="The task description")
    prompt_inputs_spec: Dict[str, str] = dspy.InputField(desc="The inputs that the prompt to test receives")
    ideas: List[str] = dspy.OutputField(type=List[str], 
                                        desc=("""
                                              List of ideas description for the test cases.
                                              Its length should be equal to num_test_cases. 
                                              Example:
                                              ```json
                                              [
                                                "Testing with technical computer science terminology",
                                                "Testing with medical research findings",
                                                "Testing with complex mathematical concepts",
                                                ...
                                              ]
                                              ```
                                            """))
class TestCase(BaseModel):
    task_description: str = Field(..., description="The task description")
    idea: str = Field(..., description="The specific idea for the test case")
    prompt_inputs: Dict[str, Any] = Field(
        ..., description="Map of required input keys to example values."
    )
    solution_criteria: List[str] = Field(
        ..., min_length=1, max_length=4, description=" Concise list of criteria (1–4 items) for evaluating the solution."
    )
    
class TestCaseSignature(dspy.Signature):
    """You are a test case creator specializing in designing evaluation scenarios.
    Generate a single test case based on the task description and a specific idea and the allowed input keys.
    """

    task_description: str = dspy.InputField(desc="The task description")
    idea: str = dspy.InputField(desc="The specific idea for the test case")
    allowed_keys: str = dspy.InputField(desc="A comma separated list of the allowed input keys")

    test_case: TestCase = dspy.OutputField(type=TestCase, desc="JSON object with fields: prompt_inputs (dict), solution_criteria (list of 1–4 strings).")    

class DatasetGenerator:
    
    def __init__(self, task_description: str, prompt_inputs_spec: dict = {}, filename:str = "dataset.json"):
        self.filename = filename
        
        self.test_designer_conversation = LoggingLM("anthropic/claude-3-5-haiku-20241022", max_tokens=1000, temperature=1.0)
        self.test_case_creator_conversation = LoggingLM("anthropic/claude-3-5-haiku-20241022", max_tokens=1000, temperature=0.7)
        self.task_description = task_description
        self.prompt_inputs_spec = prompt_inputs_spec


    def generate_unique_ideas(
        self, task_description, prompt_inputs_spec, num_cases
    ):
        """Generate a list of unique ideas for test cases based on the task description (goal)"""

        example_prompt_inputs = ""
        for key, value in prompt_inputs_spec.items():
            val = value.replace("\n", "\\n")
            example_prompt_inputs += f'"{key}": str # {val},'


        logger.info(f"Example prompt inputs for test designer: {example_prompt_inputs}")

        cot_predictor = dspy.ChainOfThought(IdeaGeneration)        
        
        message = cot_predictor(lm=self.test_designer_conversation, 
                                task_description=task_description,
                                num_test_cases=num_cases,
                                prompt_inputs_spec=example_prompt_inputs)
        
        return message.ideas


    def generate_test_case(self, task_description, idea, prompt_inputs_spec={}):
        """Generate a single test case based on the task description and a specific idea"""

        allowed_keys = ", ".join(
            [f'"{key}"' for key in prompt_inputs_spec.keys()]
        )

        trainset = [
            dspy.Example(
                task_description="Extract topics out of a passage of text",
                idea="Testing with a text that contains multiple nested topics and subtopics (e.g., a passage about renewable energy that covers solar power economics, wind turbine technology, and policy implications simultaneously)",
                allowed_keys="content",
                test_case=TestCase(
                    task_description="Extract topics out of a passage of text",
                    idea="Testing with a text that contains multiple nested topics and subtopics (e.g., a passage about renewable energy that covers solar power economics, wind turbine technology, and policy implications simultaneously)",
                    prompt_inputs={"content": "The transition to renewable energy encompasses numerous interdependent dimensions. Solar photovoltaic technology has seen dramatic cost reductions, with panel efficiency improving 24% since 2010 while manufacturing costs declined by 89%, making it economically competitive with fossil fuels in many markets. Concurrently, wind energy has evolved through innovative turbine designs featuring carbon-fiber composite blades and advanced control systems that increase energy capture by 35% in low-wind conditions."},
                    solution_criteria=["Includes all topics mentioned"]
                )
            ).with_inputs("task_description", "idea"),
        ]

        cot_predictor = dspy.ChainOfThought(TestCaseSignature)
        
        logger.info(f"Training CoT with {len(trainset)} examples")
        
        teleprompter = dspy.BootstrapFewShot()
        compiled_cot_predictor = teleprompter.compile(cot_predictor, trainset=trainset)
        
        pred = compiled_cot_predictor(lm=self.test_case_creator_conversation,
                                      task_description=task_description,
                                      idea=idea,
                                      allowed_keys=allowed_keys)

        console = Console()
        
        # Pretty print the test case data
        console.print(Panel("[bold blue]Generated Test Case[/bold blue]", border_style="blue"))
        
        # Pretty print prompt inputs
        console.print("[bold green]Test Case[/bold green]")
        console.print(f"  [cyan]{pred.test_case}[/cyan]")
                
        return pred.test_case.model_dump()

    def run(self, num_cases: int = 1, max_parallel_tasks:int = 3):
        
        ideas = self.generate_unique_ideas(
            self.task_description, self.prompt_inputs_spec, num_cases
        )

        console = Console()
        
        # Pretty print the generated ideas
        console.print(Panel("[bold green]Generated Test Ideas[/bold green]", border_style="green"))
        for i, idea in enumerate(ideas, 1):
            console.print(f"[bold cyan]{i}.[/bold cyan] {idea}")
        console.print()
        dataset = []
        completed_test_cases = 0
        total_test_cases = len(ideas)
        last_reported_percentage = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel_tasks) as executor:
            idea_future = {
                executor.submit(
                    self.generate_test_case,
                    self.task_description,
                    idea,
                    self.prompt_inputs_spec,
                ): idea
                for idea in ideas
            }
            
            for future in concurrent.futures.as_completed(idea_future):
                try:
                    result = future.result()
                    completed_test_cases += 1
                    current_percentage = int((completed_test_cases / total_test_cases) * 100)
                    milestone_percentage = (current_percentage // 20) * 20

                    if milestone_percentage > last_reported_percentage:
                        logger.info(f"Generated {completed_test_cases}/{total_test_cases} test cases")
                        last_reported_percentage = milestone_percentage

                    dataset.append(result)
                except Exception as e:
                    logger.error(f"Error generating test case: {e}")        

        with open(self.filename, "w") as f:
            json.dump(dataset, f, indent=2)
            logger.info(f"Generated dataset saved in {self.filename}")
        
        # Pretty print the final dataset summary
        console.print(Panel("[bold yellow]Dataset Generation Complete![/bold yellow]", border_style="yellow"))
        console.print(f"[green]✓ Generated {len(dataset)} test cases[/green]")
        console.print(f"[green]✓ Saved to: {self.filename}[/green]")
        
        return self.filename

if __name__ == "__main__":
    dataset_generator = DatasetGenerator(
        task_description="""Generate news digest 
        by analyzing Gmail newsletters within a specified timeframe to extract and 
        organize topic-specific news items with detailed metadata and possible local 
        events.""", 
        prompt_inputs_spec={
            "start_period": "Beginning date/timeframe for email analysis - defines the lower bound of the search window",
            "end_period": "Ending date/timeframe for email analysis - defines the upper bound of the search window", 
            "topic": "Subject matter focus for filtering newsletters and news items (e.g., 'AI news', 'tech', 'blockchain')",
            "number_of_news_items": "Maximum quantity of news items to include in the final digest output",
            "location": "Geographic area for filtering relevant local events to include in the events section"
        }, 
        filename="dataset.json"
    )
    dataset_generator.run(num_cases=3)