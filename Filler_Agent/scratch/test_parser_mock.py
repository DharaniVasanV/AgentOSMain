import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

# Mock the logger to avoid import issues
import logging
logging.basicConfig(level=logging.INFO)

from services.form_parser import _extract_questions

async def run_mock_test():
    # 1. Prepare mock elements with data-params representing different question types
    mock_blocks = []

    # Mock 1: Dropdown
    mock_dropdown_block = AsyncMock()
    # data-params format: [null, "Preferred Job Role / Title", null, 3, [[123, [["Software Engineer"], ["Product Manager"], ["Data Scientist"]]]]]
    dropdown_params = [None, "Preferred Job Role / Title", None, 3, [[123, [["Software Engineer", None, None, None, 0], ["Product Manager", None, None, None, 0], ["Data Scientist", None, None, None, 0]]]]]
    mock_dropdown_block.get_attribute.return_value = json.dumps(dropdown_params)
    mock_blocks.append(mock_dropdown_block)

    # Mock 2: Checkbox
    mock_checkbox_block = AsyncMock()
    checkbox_params = [None, "Technical Skills (Select all that apply)", None, 4, [[456, [["Python", None, None, None, 0], ["JavaScript", None, None, None, 0]]]]]
    mock_checkbox_block.get_attribute.return_value = json.dumps(checkbox_params)
    mock_blocks.append(mock_checkbox_block)

    # Mock 3: Short text (no data-params, fallback to DOM)
    mock_dom_block = AsyncMock()
    mock_dom_block.get_attribute.return_value = None
    mock_dom_block.query_selector_all.return_value = []
    
    def side_effect(selector):
        if selector.startswith('span.M7eMe') or selector.startswith('div[role="heading"]'):
            mock_heading = AsyncMock()
            mock_heading.inner_text.return_value = "Full Name *"
            return mock_heading
        return None
        
    mock_dom_block.query_selector.side_effect = side_effect
    mock_blocks.append(mock_dom_block)

    # Mock 4: DOB date field (no data-params, fallback to DOM keywords)
    mock_date_block = AsyncMock()
    mock_date_block.get_attribute.return_value = None
    mock_date_block.query_selector_all.return_value = []
    def date_side_effect(selector):
        if selector.startswith('span.M7eMe') or selector.startswith('div[role="heading"]'):
            mock_heading = AsyncMock()
            mock_heading.inner_text.return_value = "DOB *"
            return mock_heading
        return None
    mock_date_block.query_selector.side_effect = date_side_effect
    mock_blocks.append(mock_date_block)

    # 2. Mock page
    mock_page = AsyncMock()
    # query_selector_all returns mock_blocks for Strategy 1
    mock_page.query_selector_all.return_value = mock_blocks

    print("Running _extract_questions on mocked page...")
    questions = await _extract_questions(mock_page)

    print("\nExtraction results:")
    for q in questions:
        print(f"ID: {q['field_id']}")
        print(f"  Text: {q['question_text']}")
        print(f"  Type: {q['field_type']}")
        print(f"  Required: {q['is_required']}")
        print(f"  Options: {q['options']}")
        print("-" * 40)

    # Assertions
    assert questions[0]["question_text"] == "Preferred Job Role / Title"
    assert questions[0]["field_type"] == "dropdown"
    assert questions[0]["options"] == ["Software Engineer", "Product Manager", "Data Scientist"]

    assert questions[1]["question_text"] == "Technical Skills (Select all that apply)"
    assert questions[1]["field_type"] == "checkbox"
    assert questions[1]["options"] == ["Python", "JavaScript"]

    assert questions[2]["question_text"] == "Full Name"
    assert questions[2]["field_type"] == "short_text"

    assert questions[3]["question_text"] == "DOB"
    assert questions[3]["field_type"] == "date"
    
    print("\nAll unit tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_mock_test())
