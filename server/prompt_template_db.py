import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from loguru import logger


class PromptTemplateRepresentation(BaseModel):
    """Represents a prompt template with its metadata and placeholders."""
    prompt_template: str = Field(description="The actual prompt template string")
    placeholders: Dict[str, str] = Field(
        description="Dictionary mapping placeholder names to their Python type annotations",
        default_factory=dict
    )
    created_at: datetime = Field(default_factory=datetime.now, description="When this template was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="When this template was last updated")
    version: int = Field(default=1, description="Version number of this template")
    topic: str = Field(description="The topic this template is designed for")
    score: float = Field(default=0.0, description="Quality score for this template (higher is better)")


class PromptTemplateDatabase:
    """Mini-database for storing prompt templates in the filesystem."""
    
    def __init__(self, db_file: str = "prompt_templates.json"):
        self.db_file = db_file
        self.templates: Dict[str, PromptTemplateRepresentation] = {}
        try:
            self._load_templates()
        except (FileNotFoundError, Exception) as e:
            # Initialize with empty templates - database file must exist
            self.templates = {}
            logger.warning(f"Warning: {e}")
            logger.warning("Please ensure the prompt templates database file exists and contains valid data.")
    
    def _load_templates(self):
        """Load templates from the filesystem database."""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for topic, template_data in data.items():
                        # Convert string dates back to datetime objects
                        if 'created_at' in template_data:
                            template_data['created_at'] = datetime.fromisoformat(template_data['created_at'])
                        if 'updated_at' in template_data:
                            template_data['updated_at'] = datetime.fromisoformat(template_data['updated_at'])
                        
                        # Handle migration from old format
                        if 'score' not in template_data:
                            template_data['score'] = 0.0
                        
                        # Migrate old structure to new structure
                        if 'topic' not in template_data:
                            template_data['topic'] = topic
                        
                        # Create template with new key structure
                        template = PromptTemplateRepresentation(**template_data)
                        template_key = f"{template.topic}_v{template.version}"
                        self.templates[template_key] = template
                        
            except (json.JSONDecodeError, KeyError) as e:
                raise Exception(f"Failed to load prompt templates from {self.db_file}: {e}. Please ensure the file contains valid JSON data.")
        else:
            raise FileNotFoundError(f"Prompt templates database file not found: {self.db_file}. Please create the database file or run the application to initialize it.")
    
    def save(self):
        """Save templates to the filesystem database."""
        try:
            # Convert datetime objects to ISO format strings for JSON serialization
            data = {}
            for topic, template in self.templates.items():
                template_dict = template.model_dump()
                template_dict['created_at'] = template.created_at.isoformat()
                template_dict['updated_at'] = template.updated_at.isoformat()
                data[topic] = template_dict
            
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving prompt templates: {e}")
    
    def get_best_template(self, topic: str) -> PromptTemplateRepresentation:
        """Get the best prompt template for a given topic based on score."""
        if not self.templates:
            raise Exception("No prompt templates available. Please ensure the prompt templates database file exists and contains valid data.")
        
        # Find all templates for the requested topic
        topic_templates = [t for t in self.templates.values() if t.topic == topic]
        
        if not topic_templates:
            # Try to get AI news as fallback
            fallback_templates = [t for t in self.templates.values() if t.topic == "AI news"]
            if not fallback_templates:
                raise Exception(f"No prompt template found for topic '{topic}' and no fallback 'AI news' template available.")
            
            # Return the best AI news template
            best_fallback = max(fallback_templates, key=lambda t: t.score)
            return best_fallback
        
        # Return the template with the highest score for the requested topic
        best_template = max(topic_templates, key=lambda t: t.score)
        return best_template
    
    def set_template(self, topic: str, score: float, prompt_template: str, placeholders: Optional[Dict[str, str]] = None):
        """Set or create a prompt template for a topic."""
        # Find existing templates for this topic
        existing_templates = [t for t in self.templates.values() if t.topic == topic]
        
        if existing_templates:
            # Find the highest version number
            max_version = max(t.version for t in existing_templates)
            new_version = max_version + 1
        else:
            new_version = 1
        
        # Create new template with new version
        new_template = PromptTemplateRepresentation(
            prompt_template=prompt_template,
            placeholders=placeholders or {},
            topic=topic,
            version=new_version,
            score=score
        )
        
        # Use a unique key for each template (topic + version)
        template_key = f"{topic}_v{new_version}"
        self.templates[template_key] = new_template
        
        self.save()
    
    def delete_template(self, topic: str, version: Optional[int] = None) -> bool:
        """Delete a prompt template for a topic.
        
        Args:
            topic: The topic to delete
            version: Specific version to delete. If None, deletes all versions.
        """
        if topic == "AI news":
            return False  # Prevent deletion of default template
        
        if version is not None:
            # Delete specific version
            template_key = f"{topic}_v{version}"
            if template_key in self.templates:
                del self.templates[template_key]
                self.save()
                return True
            return False
        else:
            # Delete all versions of the topic
            keys_to_delete = [key for key, template in self.templates.items() 
                            if template.topic == topic]
            if keys_to_delete:
                for key in keys_to_delete:
                    del self.templates[key]
                self.save()
                return True
            return False
    
    def list_topics(self) -> list[str]:
        """List all available topics."""
        if not self.templates:
            raise Exception("No prompt templates available. Please ensure the prompt templates database file exists and contains valid data.")
        # Return unique topics, not template keys
        return list(set(template.topic for template in self.templates.values()))
    
    def get_template_info(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get metadata about the best template for a topic without the full content."""
        if not self.templates:
            raise Exception("No prompt templates available. Please ensure the prompt templates database file exists and contains valid data.")
        
        # Get the best template by score
        best_template = self.get_best_template(topic)
        
        return {
            "topic": best_template.topic,
            "version": best_template.version,
            "created_at": best_template.created_at,
            "updated_at": best_template.updated_at,
            "placeholders": best_template.placeholders,
            "template_length": len(best_template.prompt_template),
            "score": best_template.score
        }
    
    def get_all_versions(self, topic: str) -> list[PromptTemplateRepresentation]:
        """Get all versions of templates for a specific topic."""
        if not self.templates:
            raise Exception("No prompt templates available. Please ensure the prompt templates database file exists and contains valid data.")
        
        topic_templates = [t for t in self.templates.values() if t.topic == topic]
        return sorted(topic_templates, key=lambda t: t.version, reverse=True)
    
    def get_template(self, topic: str, version: int) -> Optional[PromptTemplateRepresentation]:
        """Get a specific version of a template for a topic."""
        if not self.templates:
            raise Exception("No prompt templates available. Please ensure the prompt templates database file exists and contains valid data.")
        
        for template in self.templates.values():
            if template.topic == topic and template.version == version:
                return template
        return None



# Initialize the database instance
prompt_db = PromptTemplateDatabase()
