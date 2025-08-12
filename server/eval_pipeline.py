
import concurrent.futures
import json

from statistics import mean
from typing import Callable

from loguru import logger

from server import dataset_generator
from anthropic_course.conversation import Conversation
from anthropic_course.dataset_generator import DatasetGenerator
from anthropic_course.grader import Grader
from anthropic_course.utils import generate_filename_from_prompt, generate_filename_from_prompt_function, generate_prompt_evaluation_report

class EvalPipeline:

    def __init__(self, dataset_generator:DatasetGenerator, grader:Grader, prompt_function:Callable, max_parallel_tasks:int = 3):
        self.dataset_generator = dataset_generator
        self.dataset = None
        self.grader = grader
        self.prompt_function = prompt_function
        self.max_parallel_tasks = max_parallel_tasks
        
    def load_dataset(self, dataset_file:str):
        with open(dataset_file, "r") as f:
            return json.load(f)

    def run_test_case(self, test_case, extra_criteria:str | None = None, run_syntax_grade:bool = False) -> dict:
        """Calls prompt_function, then grades the result"""
        
        logger.info(f"Running test case: {test_case}")
        prompt_generated_output = self.prompt_function(test_case["prompt_inputs"])
        
        # Grade the output
        model_grade = self.grader.grade_by_model(test_case, prompt_generated_output, extra_criteria)
        if run_syntax_grade:
            syntax_grade = self.grader.grade_syntax(test_case, prompt_generated_output)
        else:
            syntax_grade = 0
        
        # Calculate the final score
        final_score = (model_grade["score"] + syntax_grade) / (2 if run_syntax_grade else 1)
        
        return {
            "test_case": test_case,
            "generated_output": prompt_generated_output,
            "score": final_score,
            "reasoning": model_grade["reasoning"],
            "strengths": model_grade["strengths"],
            "weaknesses": model_grade["weaknesses"]
        }
    
    def run(self, extra_criteria:str | None = None, dataset_file:str | None = None, num_cases:int = 5, run_syntax_grade:bool = False) -> dict:
        """Loads the dataset and calls run_test_case with each case"""
        if not dataset_file:
            if not self.dataset:
                dataset_file = self.dataset_generator.run(num_cases=num_cases)
                self.dataset = self.load_dataset(dataset_file)
            else:
                logger.warning("Using cached dataset")
        else:
            self.dataset = self.load_dataset(dataset_file)
        
        results = []
        completed_test_cases = 0
        total_test_cases = len(self.dataset)
        last_reported_percentage = 0
        
        with concurrent.futures.ThreadPoolExecutor(
            max_workers = self.max_parallel_tasks
        ) as executor:
            test_case_future = {
                executor.submit(
                    self.run_test_case,
                    test_case,
                    extra_criteria,
                    run_syntax_grade,
                ): test_case for test_case in self.dataset
            }
            for future in concurrent.futures.as_completed(test_case_future):
                result = future.result()
                completed_test_cases += 1
                current_percentage = int((completed_test_cases / total_test_cases) * 100)
                milestone_percentage = (current_percentage // 20) * 20

                if milestone_percentage > last_reported_percentage:
                    logger.info(f"Graded {completed_test_cases}/{total_test_cases} test cases")
                    last_reported_percentage = milestone_percentage
                results.append(result)
            
        try:
            average_score = mean([result["score"] for result in results])
            logger.info(f"Average score: {average_score}")
        except KeyError as e:
            logger.error("Returned dictionary does not contain a 'score' key")
            raise Exception(e)
            
        eval_results = {
            "task_description": self.dataset_generator.task_description,
            "results": results,
            "average_score": average_score
        }
    
        html_report_filename = generate_filename_from_prompt_function(self.prompt_function, extension="html")
        html_report = generate_prompt_evaluation_report(eval_results)
        with open(html_report_filename, "w", encoding="utf-8") as f:
            f.write(html_report)
        logger.info(f"Grader Results saved in {html_report_filename}")
        
        graded_filename = generate_filename_from_prompt_function(self.prompt_function)
        with open(graded_filename, "w") as f:
            json.dump(eval_results, f, indent=2)
        logger.info(f"Grader Results saved in {graded_filename}")
        return eval_results
