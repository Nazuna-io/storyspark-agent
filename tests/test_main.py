# tests/test_main.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import json

from src.main import (
    run_agent_cycle,
    save_seeds_to_markdown,
    _ensure_data_dir,
    _save_json,
    _load_json,
    _datetime_serializer,
    _datetime_parser
)

@pytest.fixture
def mock_config():
    """Sample configuration for testing."""
    return {
        'agent': {
            'schedule_interval_minutes': 60,
            'max_sparks_per_cycle': 3,
            'run_immediately_on_start': True
        },
        'trend_detection': {
            'history_window_days': 7
        },
        'logging': {
            'output_file': 'test_sparks.md'
        }
    }

@pytest.fixture
def sample_history():
    """Sample history items."""
    return [
        {
            'title': 'Old Item',
            'timestamp': datetime.now(timezone.utc) - timedelta(days=2),
            'source': 'test_source'
        }
    ]

@pytest.fixture
def sample_new_items():
    """Sample new items."""
    return [
        {
            'title': 'New Item 1',
            'timestamp': datetime.now(timezone.utc),
            'source': 'test_source'
        },
        {
            'title': 'New Item 2',
            'timestamp': datetime.now(timezone.utc),
            'source': 'test_source'
        }
    ]

@pytest.fixture
def sample_timestamps():
    """Sample timestamp state."""
    return {
        'test_source': datetime.now(timezone.utc) - timedelta(days=1)
    }

@pytest.fixture
def sample_seeds():
    """Sample story seeds."""
    return [
        {
            'spark_keyword': 'test',
            'source_name': 'test_source',
            'logline': 'A test story',
            'what_if_questions': ['What if test?', 'What if another test?'],
            'thematic_keywords': ['testing', 'experiment'],
            'generation_timestamp': datetime.now(timezone.utc)
        }
    ]

class TestDatetimeSerialization:
    """Test datetime serialization helpers."""
    
    def test_datetime_serializer(self):
        """Test datetime to JSON serialization."""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = _datetime_serializer(dt)
        assert result == '2024-01-01T12:00:00+00:00'
    
    def test_datetime_serializer_naive(self):
        """Test naive datetime serialization."""
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = _datetime_serializer(dt)
        assert result == '2024-01-01T12:00:00'
    
    def test_datetime_serializer_invalid_type(self):
        """Test serializer with invalid type."""
        with pytest.raises(TypeError):
            _datetime_serializer("not a datetime")
    
    def test_datetime_parser(self):
        """Test JSON to datetime parsing."""
        data = {
            'timestamp': '2024-01-01T12:00:00+00:00',
            'other_field': 'test'
        }
        result = _datetime_parser(data)
        assert isinstance(result['timestamp'], datetime)
        assert result['timestamp'] == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert result['other_field'] == 'test'
    
    def test_datetime_parser_invalid_format(self):
        """Test parser with invalid datetime format."""
        data = {
            'timestamp': 'invalid-datetime',
            'other_field': 'test'
        }
        result = _datetime_parser(data)
        assert result['timestamp'] == 'invalid-datetime'  # Should remain unchanged
        assert result['other_field'] == 'test'

class TestFileOperations:
    """Test file operation helpers."""
    
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_ensure_data_dir_creates(self, mock_makedirs, mock_exists):
        """Test data directory creation."""
        mock_exists.return_value = False
        _ensure_data_dir()
        mock_makedirs.assert_called_once_with('data')
    
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_ensure_data_dir_exists(self, mock_makedirs, mock_exists):
        """Test when data directory already exists."""
        mock_exists.return_value = True
        _ensure_data_dir()
        mock_makedirs.assert_not_called()
    
    def test_save_json(self, tmp_path):
        """Test JSON saving."""
        test_file = tmp_path / "test.json"
        data = {'key': 'value', 'timestamp': datetime.now(timezone.utc)}
        
        _save_json(data, str(test_file))
        
        # Verify file exists and contains correct data
        assert test_file.exists()
        loaded_data = json.loads(test_file.read_text())
        assert loaded_data['key'] == 'value'
        assert 'timestamp' in loaded_data
    
    def test_load_json_exists(self, tmp_path):
        """Test loading existing JSON file."""
        test_file = tmp_path / "test.json"
        data = {'key': 'value'}
        test_file.write_text(json.dumps(data))
        
        result = _load_json(str(test_file))
        assert result == data
    
    def test_load_json_not_exists(self):
        """Test loading non-existent JSON file."""
        result = _load_json('/nonexistent/file.json', default={'default': 'value'})
        assert result == {'default': 'value'}
    
    def test_load_json_invalid_format(self, tmp_path):
        """Test loading invalid JSON file."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("invalid json content")
        
        result = _load_json(str(test_file), default={'default': 'value'})
        assert result == {'default': 'value'}

class TestSaveSeedsToMarkdown:
    """Test markdown saving functionality."""
    
    def test_save_seeds_empty(self, tmp_path):
        """Test saving empty seeds list."""
        output_file = tmp_path / "test_sparks.md"
        save_seeds_to_markdown([], str(output_file))
        
        content = output_file.read_text()
        assert "No story seeds generated yet" in content
    
    def test_save_seeds_with_data(self, tmp_path, sample_seeds):
        """Test saving seeds to markdown."""
        output_file = tmp_path / "test_sparks.md"
        save_seeds_to_markdown(sample_seeds, str(output_file))
        
        content = output_file.read_text()
        assert "test" in content
        assert "A test story" in content
        assert "What if test?" in content
        assert "testing" in content
    
    def test_save_seeds_multiple(self, tmp_path):
        """Test saving multiple seeds."""
        seeds = [
            {
                'spark_keyword': 'ai',
                'source_name': 'tech_source',
                'logline': 'AI becomes sentient',
                'what_if_questions': ['What if AI?'],
                'thematic_keywords': ['artificial', 'intelligence']
            },
            {
                'spark_keyword': 'quantum',
                'source_name': 'science_source',
                'logline': 'Quantum breakthrough',
                'what_if_questions': ['What if quantum?'],
                'thematic_keywords': ['physics', 'quantum']
            }
        ]
        
        output_file = tmp_path / "test_sparks.md"
        save_seeds_to_markdown(seeds, str(output_file))
        
        content = output_file.read_text()
        assert "ai" in content
        assert "quantum" in content
        assert "AI becomes sentient" in content
        assert "Quantum breakthrough" in content

class TestRunAgentCycle:
    """Test the main agent cycle function."""
    
    @patch('src.main.get_new_items')
    @patch('src.main.detect_sparks')
    @patch('src.main.generate_story_seed')
    @patch('src.main.configure_genai')
    def test_run_cycle_no_new_items(self, mock_configure, mock_generate, mock_detect, mock_get_items,
                                   mock_config, sample_history, sample_timestamps):
        """Test cycle with no new items."""
        mock_get_items.return_value = ([], sample_timestamps)
        
        history, timestamps, seeds = run_agent_cycle(mock_config, sample_history, sample_timestamps)
        
        assert history == sample_history
        assert timestamps == sample_timestamps
        assert seeds == []
        mock_detect.assert_not_called()
        mock_generate.assert_not_called()
    
    @patch('src.main.get_new_items')
    @patch('src.main.detect_sparks')
    @patch('src.main.generate_story_seed')
    @patch('src.main.configure_genai')
    def test_run_cycle_no_sparks(self, mock_configure, mock_generate, mock_detect, mock_get_items,
                                mock_config, sample_history, sample_timestamps, sample_new_items):
        """Test cycle with new items but no sparks."""
        mock_get_items.return_value = (sample_new_items, sample_timestamps)
        mock_detect.return_value = []
        
        history, timestamps, seeds = run_agent_cycle(mock_config, sample_history, sample_timestamps)
        
        assert len(history) == len(sample_history) + len(sample_new_items)
        assert timestamps == sample_timestamps
        assert seeds == []
        mock_generate.assert_not_called()
    
    @patch('src.main.get_new_items')
    @patch('src.main.detect_sparks')
    @patch('src.main.generate_story_seed')
    @patch('src.main.configure_genai')
    def test_run_cycle_with_sparks(self, mock_configure, mock_generate, mock_detect, mock_get_items,
                                  mock_config, sample_history, sample_timestamps, sample_new_items):
        """Test cycle with sparks and seed generation."""
        mock_get_items.return_value = (sample_new_items, sample_timestamps)
        mock_sparks = [
            {'keyword': 'test1', 'source_name': 'source1'},
            {'keyword': 'test2', 'source_name': 'source2'}
        ]
        mock_detect.return_value = mock_sparks
        mock_configure.return_value = True
        mock_generate.side_effect = [
            {'spark_keyword': 'test1', 'logline': 'Story 1'},
            {'spark_keyword': 'test2', 'logline': 'Story 2'}
        ]
        
        history, timestamps, seeds = run_agent_cycle(mock_config, sample_history, sample_timestamps)
        
        assert len(seeds) == 2
        assert seeds[0]['spark_keyword'] == 'test1'
        assert seeds[1]['spark_keyword'] == 'test2'
        assert mock_generate.call_count == 2
    
    @patch('src.main.get_new_items')
    @patch('src.main.detect_sparks')
    @patch('src.main.generate_story_seed')
    @patch('src.main.configure_genai')
    def test_run_cycle_max_sparks_limit(self, mock_configure, mock_generate, mock_detect, mock_get_items,
                                       mock_config, sample_history, sample_timestamps, sample_new_items):
        """Test cycle respects max sparks per cycle limit."""
        mock_config['agent']['max_sparks_per_cycle'] = 2
        mock_get_items.return_value = (sample_new_items, sample_timestamps)
        
        # Return more sparks than the limit
        mock_sparks = [
            {'keyword': 'test1', 'source_name': 'source1'},
            {'keyword': 'test2', 'source_name': 'source2'},
            {'keyword': 'test3', 'source_name': 'source3'},
            {'keyword': 'test4', 'source_name': 'source4'}
        ]
        mock_detect.return_value = mock_sparks
        mock_configure.return_value = True
        mock_generate.side_effect = [
            {'spark_keyword': 'test1', 'logline': 'Story 1'},
            {'spark_keyword': 'test2', 'logline': 'Story 2'}
        ]
        
        history, timestamps, seeds = run_agent_cycle(mock_config, sample_history, sample_timestamps)
        
        # Should only process 2 sparks
        assert len(seeds) == 2
        assert mock_generate.call_count == 2
    
    @patch('src.main.get_new_items')
    @patch('src.main.detect_sparks') 
    @patch('src.main.configure_genai')
    def test_run_cycle_history_window(self, mock_configure, mock_detect, mock_get_items,
                                     mock_config):
        """Test history window pruning."""
        # Create history with items older than window
        old_item = {
            'title': 'Very Old Item',
            'timestamp': datetime.now(timezone.utc) - timedelta(days=10),
            'source': 'test_source'
        }
        recent_item = {
            'title': 'Recent Item',
            'timestamp': datetime.now(timezone.utc) - timedelta(days=2),
            'source': 'test_source'
        }
        history = [old_item, recent_item]
        
        new_items = [{
            'title': 'New Item',
            'timestamp': datetime.now(timezone.utc),
            'source': 'test_source'
        }]
        
        mock_get_items.return_value = (new_items, {'test_source': datetime.now(timezone.utc)})
        mock_detect.return_value = []
        
        updated_history, _, _ = run_agent_cycle(mock_config, history, {})
        
        # Old item should be pruned
        assert len(updated_history) == 2  # Recent item + new item
        assert old_item not in updated_history
        assert recent_item in updated_history
        assert new_items[0] in updated_history
    
    @patch('src.main.get_new_items')
    @patch('src.main.detect_sparks')
    @patch('src.main.generate_story_seed')
    @patch('src.main.configure_genai')
    def test_run_cycle_api_configuration_failure(self, mock_configure, mock_generate, mock_detect, 
                                               mock_get_items, mock_config, sample_history, 
                                               sample_timestamps, sample_new_items):
        """Test cycle when API configuration fails."""
        mock_get_items.return_value = (sample_new_items, sample_timestamps)
        mock_sparks = [{'keyword': 'test', 'source_name': 'source'}]
        mock_detect.return_value = mock_sparks
        mock_configure.return_value = False  # API configuration fails
        
        history, timestamps, seeds = run_agent_cycle(mock_config, sample_history, sample_timestamps)
        
        assert seeds == []  # No seeds generated
        mock_generate.assert_not_called()  # Should not attempt to generate

class TestScheduledJob:
    """Test the scheduled job function behavior."""
    
    @patch('src.main.run_agent_cycle')
    @patch('src.main.save_fetcher_state')
    @patch('src.main._save_json')
    @patch('src.main.save_seeds_to_markdown')
    def test_scheduled_job_success(self, mock_save_markdown, mock_save_json, mock_save_state,
                                  mock_run_cycle, mock_config):
        """Test successful scheduled job execution."""
        # Mock the run_agent_cycle return values
        new_history = [{'title': 'New Item'}]
        new_timestamps = {'source': datetime.now(timezone.utc)}
        new_seeds = [{'spark_keyword': 'test', 'logline': 'Test story'}]
        mock_run_cycle.return_value = (new_history, new_timestamps, new_seeds)
        
        # Create the scheduled job function as it would be in main()
        state_container = {'history': [], 'timestamps': {}}
        all_generated_seeds = []
        
        def scheduled_job():
            updated_history, updated_timestamps, new_seeds = mock_run_cycle(
                mock_config,
                state_container['history'],
                state_container['timestamps']
            )
            state_container['history'] = updated_history
            state_container['timestamps'] = updated_timestamps
            
            mock_save_state(updated_timestamps, 'data/fetcher_state.json')
            mock_save_json(updated_history, 'data/history_items.json')
            
            if new_seeds:
                all_generated_seeds.extend(new_seeds)
                mock_save_json(all_generated_seeds, 'data/generated_seeds.json')
                mock_save_markdown(all_generated_seeds, mock_config['logging']['output_file'])
        
        # Run the job
        scheduled_job()
        
        # Verify state was updated
        assert state_container['history'] == new_history
        assert state_container['timestamps'] == new_timestamps
        assert len(all_generated_seeds) == 1
        
        # Verify save functions were called
        mock_save_state.assert_called_once()
        assert mock_save_json.call_count == 2  # history and seeds
        mock_save_markdown.assert_called_once()
