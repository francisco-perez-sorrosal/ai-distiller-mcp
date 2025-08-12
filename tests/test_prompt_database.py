#!/usr/bin/env python3
"""
Test script for the prompt template database functionality.
This demonstrates how to use the mini-database for storing and managing prompt templates.
"""

import json
import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.prompt_template_db import prompt_db
from server.utils import (
    get_best_prompt_template,
    set_prompt_template,
    get_current_prompt
)

def test_database_initialization():
    """Test database initialization."""
    print("🧪 Testing database initialization...")
    
    # Check if database has templates
    if not prompt_db.templates:
        print("❌ Database is empty - no templates found")
        return False
    else:
        print("✅ Database loaded successfully with existing templates")
    
    return True

def test_database_loading():
    """Test database loading from existing JSON file."""
    print("🧪 Testing database loading from JSON file...")
    
    try:
        # Test getting a specific template
        ai_news = prompt_db.get_best_template("AI news")
        print(f"✅ AI news template loaded successfully")
        print(f"   Template length: {len(ai_news.prompt_template)}")
        print(f"   Placeholders: {ai_news.placeholders}")
        
        # Test listing topics
        topics = prompt_db.list_topics()
        print(f"✅ Available topics: {topics}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading from database: {e}")
        return False

def test_scoring_functionality():
    """Test the new scoring and version management functionality."""
    print("\n🎯 Testing scoring and version management...")
    
    try:
        # Add multiple versions of the same topic with different scores
        set_prompt_template(
            "research papers",
            7.0,
            "Analyze {count} research papers on {subject} published between {start_year} and {end_year}. Extract key findings and methodologies.",
            {
                "count": "int",
                "subject": "str",
                "start_year": "int",
                "end_year": "int"
            }
        )
        print("✅ Added 'research papers' v1 with score 7.0")
        
        # Add a better version
        set_prompt_template(
            "research papers",
            9.2,
            "Analyze {count} research papers on {subject} published between {start_year} and {end_year}. Extract key findings, methodologies, and provide critical analysis.",
            {
                "count": "int",
                "subject": "str",
                "start_year": "int",
                "end_year": "int"
            }
        )
        print("✅ Added 'research papers' v2 with score 9.2")
        
        # Test that the best template (highest score) is returned
        best_research = prompt_db.get_best_template("research papers")
        print(f"✅ Best research template: v{best_research.version} with score {best_research.score}")
        
        # Test getting all versions
        all_versions = prompt_db.get_all_versions("research papers")
        print(f"✅ All versions: {[f'v{t.version}({t.score})' for t in all_versions]}")
        
        # Test getting specific version
        v1_template = prompt_db.get_template("research papers", 1)
        if v1_template:
            print(f"✅ Retrieved v1 template with score {v1_template.score}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing scoring functionality: {e}")
        return False

def test_basic_operations():
    """Test basic database operations."""
    print("🧪 Testing basic database operations...")
    
    # List current topics
    try:
        topics = prompt_db.list_topics()
        print(f"📋 Available topics: {topics}")
    except Exception as e:
        print(f"❌ Error listing topics: {e}")
        return False
    
    # Get metadata for AI news template
    try:
        metadata = prompt_db.get_template_info("AI news")
        print(f"📊 AI news template metadata: {json.dumps(metadata, indent=2, default=str)}")
    except Exception as e:
        print(f"❌ Error getting metadata: {e}")
        return False
    
    # Add a new topic template
    try:
        set_prompt_template(
            "tech news",
            8.5,
            "Summarize {number} tech articles about {topic} from {start_date} to {end_date}. Focus on {focus_area}.",
            {
                "number": "int",
                "topic": "str", 
                "start_date": "str",
                "end_date": "str",
                "focus_area": "str"
            }
        )
        print("✅ Added new 'tech news' template with score 8.5")
    except Exception as e:
        print(f"❌ Error adding template: {e}")
        return False
    
    # List updated topics
    try:
        updated_topics = prompt_db.list_topics()
        print(f"📋 Updated topics: {updated_topics}")
    except Exception as e:
        print(f"❌ Error listing updated topics: {e}")
        return False
    
    # Get the new template
    try:
        tech_template = prompt_db.get_best_template("tech news")
        print(f"📝 Tech news template: {tech_template.prompt_template}")
        print(f"🔧 Placeholders: {tech_template.placeholders}")
    except Exception as e:
        print(f"❌ Error getting template: {e}")
        return False
    
    return True

def test_advanced_operations():
    """Test advanced database operations."""
    print("\n🚀 Testing advanced database operations...")
    
    # Create a backup
    try:
        import shutil
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"prompt_templates_backup_{timestamp}.json"
        shutil.copy2(prompt_db.db_file, backup_file)
        print(f"💾 Created backup: {backup_file}")
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return False
    

    
    # Add another template
    try:
        set_prompt_template(
            "research papers",
            0.0,
            "Analyze {count} research papers on {subject} published between {start_year} and {end_year}. Extract key findings and methodologies.",
            {
                "count": "int",
                "subject": "str",
                "start_year": "int",
                "end_year": "int"
            }
        )
        print("✅ Added 'research papers' template")
    except Exception as e:
        print(f"❌ Error adding research papers template: {e}")
        return False
    
    # Show final state
    try:
        final_topics = prompt_db.list_topics()
        print(f"📋 Final topics: {final_topics}")
    except Exception as e:
        print(f"❌ Error listing final topics: {e}")
        return False
    
    return True

def test_template_formatting():
    """Test template formatting with placeholders."""
    print("\n🎯 Testing template formatting...")
    
    # Get a template and format it
    try:
        template = prompt_db.get_best_template("tech news")
        formatted_prompt = template.prompt_template.format(
            number=5,
            topic="artificial intelligence",
            start_date="2024-01-01",
            end_date="2024-01-31",
            focus_area="machine learning applications"
        )
        
        print(f"📝 Formatted prompt:\n{formatted_prompt}")
        return True
    except Exception as e:
        print(f"❌ Error formatting template: {e}")
        return False

if __name__ == "__main__":
    print("🎬 Starting prompt template database tests...\n")
    
    try:
        # Test initialization first
        if not test_database_initialization():
            print("❌ Database initialization failed. Exiting.")
            sys.exit(1)
        
        # Run other tests
        if (test_database_loading() and test_scoring_functionality() and test_basic_operations() and 
            test_advanced_operations() and test_template_formatting()):
            print("\n🎉 All tests completed successfully!")
            print(f"📁 Database file: {prompt_db.db_file}")
            print(f"📊 Total templates: {len(prompt_db.templates)}")
        else:
            print("\n❌ Some tests failed.")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
