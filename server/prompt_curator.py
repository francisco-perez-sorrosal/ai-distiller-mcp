
import dspy
from loguru import logger

class CuratePrompt(dspy.Signature):
    """Review the prompt passed and carefully update it based on the user feedback. 
    Feedback is a string that contains the strengths, weaknesses, and suggestions for the prompt.
    Cluster first all, the strengths, weakneses, and suggestions, eliminating possible duplications.
    Then proceed to update the prompt based on all the information gathered.
    """
    prompt: str = dspy.InputField(description="Current prompt to review")
    feedback: str = dspy.InputField(description="User feedback to review the prompt for")
    # Output
    updated_prompt: str = dspy.OutputField(description="Updated prompt")


class PromptCurator(dspy.Module):
    def __init__(self):
        super().__init__()
        self.curate_prompt = dspy.ChainOfThought(CuratePrompt)
    
    def forward(self, prompt: str, feedback: str) -> str:
        """Process prompt through the review pipeline to extract relevant content.
        
        Args:
            prompt (str): The prompt to review.
            feedback (str): The user feedback to review the prompt for.
        
        Returns:
            str: The updated prompt.
        
        Raises:
            Exception: If there's an error in the prompt review process.
        
        Example:
            >>> prompt_curator = PromptCurator()
            >>> result = prompt_curator.forward("Current prompt", "User feedback")
        """
        logger.info(f"Calling curate_prompt with {prompt}, {feedback}")
        result = self.curate_prompt(prompt=prompt, feedback=feedback)
        logger.info("--------------------------------")
        logger.info(f"Prompt curator type: {type(result)}")
        logger.info(f"Prompt curator content: {result.updated_prompt}")
        logger.info("--------------------------------")
                    
        return result.updated_prompt
    