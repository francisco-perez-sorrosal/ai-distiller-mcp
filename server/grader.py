import ast
import re
import json
from textwrap import dedent
from typing import Any, Dict, List

import dspy
from loguru import logger
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel

from server.utils import LoggingLM, render


class TestCaseScores(BaseModel):
    strengths: List[str] = Field(..., min_length=1, max_length=10, description="A list of strengths of the solution")
    weaknesses: List[str] = Field(..., min_length=1, max_length=10, description="A list of weaknesses of the solution")
    reasoning: str = Field(..., description="A concise explanation of the evaluation")
    score: int = Field(..., description="""A number between 1-10, being 10 the best score
                       Scoring Guidelines:
                       * Score 1-3: Solution fails to meet one or more MANDATORY requirements
                       * Score 4-6: Solution meets all mandatory requirements but has significant deficiencies in secondary criteria
                       * Score 7-8: Solution meets all mandatory requirements and most secondary criteria, with minor issues
                       * Score 9-10: Solution meets all mandatory and secondary criteria

                       IMPORTANT SCORING INSTRUCTIONS:
                       * Grade the output based ONLY on the listed criteria. Do not add your own extra requirements.
                       * If a solution meets all of the mandatory and secondary criteria give it a 10
                       * Don't complain that the solution "only" meets the mandatory and secondary criteria. 
                         Solutions shouldn't go above and beyond - they should meet the exact listed criteria.
                       * ANY violation of a mandatory requirement MUST result in a score of 3 or lower
                       * The full 1-10 scale should be utilized - don't hesitate to give low scores when warranted
                       """)

class PromptEvaluationSignature(dspy.Signature):
    """Your task is to evaluate the following AI-generated solution with EXTREME RIGOR.
    """

    task_description: str = dspy.InputField(desc="The task description")
    prompt_inputs: Dict[str, Any] = dspy.InputField(desc="The inputs that the prompt to test receives")
    solution: str = dspy.InputField(desc="The solution to evaluate")
    solution_criteria: List[str] = dspy.InputField(desc="The criteria to evaluate the solution")
    extra_criteria: str = dspy.InputField(desc="Optional extra criteria to evaluate the solution")

    evaluation: TestCaseScores = dspy.OutputField(type=TestCaseScores, desc="JSON object with fields: strengths (list of strings), weaknesses (list of strings), reasoning (string), score (number).")   


class Grader:
    
    def __init__(self):      
        self.grader_lm = LoggingLM("anthropic/claude-3-5-haiku-20241022", max_tokens=1000, temperature=1.0)
    
    def grade_by_model(self, test_case, llm_output, extra_criteria=None) -> TestCaseScores:
        
        extra_criteria_section = ""
        if extra_criteria:
            extra_criteria_template = """
            Mandatory Requirements - ANY VIOLATION MEANS AUTOMATIC FAILURE (score of 3 or lower):
            <extra_important_criteria>
            {extra_criteria}
            </extra_important_criteria>
            """
            extra_criteria_section = render(
                dedent(extra_criteria_template),
                {"extra_criteria": extra_criteria},
            )

        cot_predictor = dspy.ChainOfThought(PromptEvaluationSignature)        
        
        message = cot_predictor(lm=self.grader_lm, 
                                task_description=test_case["task_description"],
                                prompt_inputs=test_case["prompt_inputs"],
                                solution=llm_output,
                                solution_criteria=test_case["solution_criteria"],
                                extra_criteria=extra_criteria_section)

        return message.evaluation


if __name__ == "__main__":
    grader = Grader()
    
    test_case = {
        "task_description": "Generate news digest by analyzing Gmail newsletters within a specified timeframe to extract and organize topic-specific news items with detailed metadata and possible local events",
        "prompt_inputs": {
            "start_period": "2023-06-01",
            "end_period": "2023-09-15",
            "topic": "AI News",
            "number_of_news_items": 3,
            "location": "San Francisco"
        },
        "solution_criteria": [
            "Covers multiple geographical regions",
            "Includes at least 3 distinct AI news topics",
            "Provides publication dates and source metadata",
            "Highlights local event implications for each news item"
        ]
    }
    
    
    llm_output = """
    Based on my analysis of your emails from the last couple of days, here's a detailed breakdown of your email sources:
    Email Summary (Last 2 Days)
    Total emails received: 10
    Breakdown by Email Source:

    Meetup: 2 emails

    AI, Machine Learning and Computer Vision Meetup Network
    Bay Area Friends of Europe


    Individual sources (1 email each):

    ResearchGate
    AGI House
    The Information
    Hugging Face Forums
    Medium Newsletter
    Machine Cinema
    Luma (Event Platform)
    Generative AI Newsletter



    Breakdown by Category:

    Updates: 8 emails (80%)
    Social: 2 emails (20%)

    Detailed Email List:

    ResearchGate - Weekly stats report about people reading your work
    AGI House - Newsletter about AI events, red carpet gala, AI BBQ
    The Information - Business briefing about Meta's AI investments
    Meetup (AI/ML) - Virtual workshop on building GUI agents
    Hugging Face Forums - Weekly forum summary with AI research topics
    Medium Newsletter - Article digest about decision-making and anxiety
    Machine Cinema - Newsletter about AI in creative industries and filmmaking
    Luma - Event registration confirmation for MCP Discovery Hack Night
    Meetup (Bay Area Friends of Europe) - Social event invitation
    Generative AI Newsletter - AI news about Google's Perch model and Duolingo

    Most of your emails are AI and tech-focused newsletters and updates (80%), with a smaller portion being social/professional networking emails (20%). The content is primarily centered around artificial intelligence, machine learning, research, and tech industry news.    
    """
    
    message = grader.grade_by_model(
        test_case=test_case,
        llm_output=llm_output,
        extra_criteria=None
    )
   
    console = Console()
    console.print(Panel("[bold blue]Prompt Grade[/bold blue]", border_style="blue"))
    console.print(f"   [cyan]{message}[/cyan]")
