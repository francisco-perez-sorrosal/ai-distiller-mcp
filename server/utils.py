import json
import re

from datetime import datetime, timedelta
from typing import Optional, Dict

import dspy
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from .prompt_template_db import PromptTemplateRepresentation, prompt_db


class LoggingLM(dspy.LM):
    console = Console()
    def __call__(self, *args, **kwargs):
        
        value = kwargs.get('prompt') or kwargs
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                self.console.print(Panel(f"Prompt:\n{json.dumps(parsed, indent=4)}"))
            except json.JSONDecodeError:
                # Not JSON, just print the string
                self.console.print(Panel(f"Prompt:\n{value}"))
        elif isinstance(value, dict):
            self.console.print(Panel(f"Prompt:\n{json.dumps(value, indent=4)}"))
        else:
            self.console.print(Panel(f"Prompt:\n{value}"))

        return super().__call__(*args, **kwargs)


def render(template_string, variables):
    placeholders = re.findall(r"{([^{}]+)}", template_string)

    result = template_string
    for placeholder in placeholders:
        if placeholder in variables:
            result = result.replace(
                "{" + placeholder + "}", str(variables[placeholder])
            )

    return result.replace("{{", "{").replace("}}", "}")

def ensure_datetime(date_string: str) -> datetime:
    """Parse date string in various formats and return a datetime object."""
    
    match date_string:
        case "today":
            return datetime.now()
        case "yesterday":
            return datetime.now() - timedelta(days=1)
        case "last_week":
            return datetime.now() - timedelta(days=7)
        case "last_month":
            return datetime.now() - timedelta(days=30)
        case "last_year":
            return datetime.now() - timedelta(days=365)
        case _:
            logger.info(f"Parsing date: {date_string}")            
            formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y-%m-%d %H:%M:%S',
                '%m/%d/%Y %H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_string, fmt)
                except ValueError:
                    continue
            
            raise ValueError(f"Unable to parse date: {date_string}")




def build_prompt(topic: str, version: int | None = None, start_period: str = "yesterday", end_period: str = "today", number_of_news_items: int = 10, location: str = "San Francisco") -> str:
    """Build the prompt with placeholders filled in from the database."""
    template = prompt_db.get_template(topic, version) if version else prompt_db.get_latest_template(topic)
    if template is None:
        raise ValueError(f"No template found for topic {topic} and version {version}")
    
    return template.prompt_template.format(
        start_period=start_period,
        end_period=end_period,
        topic=topic,
        number_of_news_items=number_of_news_items,
        location=location
    )

def get_latest_prompt_template(topic: str) -> PromptTemplateRepresentation:
    """Retrieve the latest prompt template for the topic from the database."""
    return prompt_db.get_latest_template(topic)
    

def set_prompt_template(topic: str, prompt: str, placeholders: Optional[Dict[str, str]] = None):
    """Set the prompt template for the topic in the database."""
    prompt_db.set_template(topic, prompt, placeholders)
    prompt_db.save()

