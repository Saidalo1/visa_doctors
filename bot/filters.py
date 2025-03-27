"""Filter manager for survey submissions."""
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Any, Optional

from asgiref.sync import sync_to_async
from django.db.models import Q, QuerySet

from app.models import SurveySubmission, Question, AnswerOption

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG to show all logs

# Create logs directory if it doesn't exist
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Create rotating file handler
file_handler = RotatingFileHandler(
    filename=os.path.join(log_dir, 'bot.log'),
    maxBytes=5*1024*1024,  # 5MB
    backupCount=3,  # Keep 3 backup files
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add console handler for all logs
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)  # Show all logs
console_handler.setFormatter(formatter)

# Remove any existing handlers
logger.handlers = []
logger.addHandler(console_handler)

# Disable propagation to root logger to avoid duplicate logs
logger.propagate = False

class SurveyFilter:
    """Filter manager for survey submissions."""
    
    def __init__(self, state: Dict[str, Any] = None):
        """Initialize filter manager."""
        logger.debug(f"Initializing SurveyFilter with state: {state}")
        
        if state is None:
            state = {
                'date_filters': {},
                'response_filters': {},
                'selected_dates': [],
                'status_filter': None
            }
        
        self.date_filters = state.get('date_filters', {})
        self.response_filters = {}  # Will be populated from response_filters_data
        self._response_filters_data = state.get('response_filters', {})  # Store IDs instead of objects
        self.selected_dates = set(state.get('selected_dates', []))  # Store selected dates
        self._questions = None  # Lazy load questions
        self._status_filter = state.get('status_filter')  # Store status filter
        
        logger.debug(f"Initialized with date_filters: {self.date_filters}")
        logger.debug(f"Initialized with selected_dates: {self.selected_dates}")
        logger.debug(f"Initialized with response_filters_data: {self._response_filters_data}")
        
    @property
    def questions(self):
        """Lazy load questions."""
        if self._questions is None:
            self._questions = Question.objects.select_related('field_type').all()
        return self._questions
        
    def get_state(self) -> Dict[str, Any]:
        """Get serializable state of the filter manager."""
        state = {
            'date_filters': self.date_filters,
            'response_filters': self._response_filters_data,
            'selected_dates': list(self.selected_dates),  # Convert set to list for JSON serialization
            'status_filter': self._status_filter
        }
        logger.debug(f"Getting state: {state}")
        return state
        
    @sync_to_async
    def get_active_filters(self) -> List[Dict[str, Any]]:
        """Get list of active filters."""
        active_filters = []
        
        # Add status filter if set
        if hasattr(self, '_status_filter') and self._status_filter:
            status_display = dict(SurveySubmission.Status.choices)[self._status_filter]
            active_filters.append({
                'name': 'Статус',
                'value': status_display
            })
        
        # Add date filters
        date_ranges = {}
        for field, value in self.date_filters.items():
            base_field = field[:-5]  # Remove __gte or __lte
            if base_field not in date_ranges:
                date_ranges[base_field] = {'name': 'Дата создания' if base_field == 'created_at' else 'Дата обновления'}
            
            if field.endswith('__gte'):
                date_ranges[base_field]['start'] = value
            else:
                date_ranges[base_field]['end'] = value
                
        # Format date ranges
        for field_data in date_ranges.values():
            value = ""
            if 'start' in field_data:
                start_date = datetime.strptime(field_data['start'], "%Y-%m-%d")
                value = f"от {start_date.strftime('%d.%m.%Y')}"
            if 'end' in field_data:
                end_date = datetime.strptime(field_data['end'], "%Y-%m-%d")
                value += f"{' ' if value else ''}до {end_date.strftime('%d.%m.%Y')}"
                
            active_filters.append({
                'name': field_data['name'],
                'value': value
            })
            
        # Add response filters
        for question_id, filters_list in self._response_filters_data.items():
            try:
                question = Question.objects.get(id=int(question_id))
                values = [f['value'] for f in filters_list]
                active_filters.append({
                    'name': question.field_type.title,
                    'value': ', '.join(values)
                })
            except Question.DoesNotExist:
                continue
                
        return active_filters
        
    @sync_to_async
    def add_date_filter(self, field: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> None:
        """Add date filter."""
        logger.debug(f"Adding date filter - field: {field}, start: {start_date}, end: {end_date}")
        logger.debug(f"Before adding - date_filters: {self.date_filters}")
        logger.debug(f"Before adding - selected_dates: {self.selected_dates}")
        
        if not any([start_date, end_date]):
            return
            
        # Clear existing date filters for this field
        field_filters = [f"{field}__gte", f"{field}__lte"]
        for key in field_filters:
            if key in self.date_filters:
                del self.date_filters[key]
                
        if start_date:
            self.date_filters[f"{field}__gte"] = start_date
            self.selected_dates.add(start_date)
            
        if end_date:
            self.date_filters[f"{field}__lte"] = end_date
            self.selected_dates.add(end_date)
            
        logger.debug(f"After adding - date_filters: {self.date_filters}")
        logger.debug(f"After adding - selected_dates: {self.selected_dates}")
        
    @sync_to_async
    def add_response_filter(self, question_id: int, value: str) -> None:
        """Add response filter."""
        logger.debug(f"Adding response filter - question_id: {question_id}, value: {value}")
        logger.debug(f"Current response filters: {self._response_filters_data}")
        
        try:
            question = Question.objects.get(id=question_id)
            
            # For text questions, store the value directly
            if question.input_type in ['text', 'number', 'phone']:
                self._response_filters_data[str(question_id)] = [{
                    'value': value,
                    'question_id': question_id
                }]
            # For choice questions, store the option ID and value
            else:
                self._response_filters_data[str(question_id)] = [{
                    'value': value,
                    'question_id': question_id,
                    'option_id': value  # For choice questions, value is the option ID
                }]
            
            logger.debug(f"Updated response filters: {self._response_filters_data}")
            
        except Question.DoesNotExist:
            logger.error(f"Question {question_id} not found")
            pass
            
    @sync_to_async
    def get_filtered_submissions(self) -> QuerySet:
        """Get submissions filtered by all active filters."""
        logger.debug("Getting filtered submissions")
        logger.debug(f"Date filters: {self.date_filters}")
        logger.debug(f"Response filters: {self._response_filters_data}")
        logger.debug(f"Status filter: {self._status_filter}")
        
        # Start with all submissions
        queryset = SurveySubmission.objects.all()
        
        # Apply date filters if present
        if self.date_filters:
            queryset = queryset.filter(**self.date_filters)
            
        # Apply status filter if present
        if self._status_filter:
            queryset = queryset.filter(status=self._status_filter)
            
        # Apply response filters
        for question_id, filters in self._response_filters_data.items():
            # Create OR conditions for all options of this question
            if filters:
                conditions = Q()
                for filter_data in filters:
                    if 'option_id' in filter_data:
                        # For choice questions
                        conditions |= Q(
                            responses__question_id=filter_data['question_id'],
                            responses__selected_options__id=filter_data['option_id']
                        )
                    else:
                        # For text questions
                        value = filter_data['value']
                        conditions |= Q(
                            responses__question_id=filter_data['question_id'],
                            responses__text_answer__icontains=value
                        )
                queryset = queryset.filter(conditions)
        
        # Ensure distinct results
        return queryset.distinct()
        
    @sync_to_async
    def get_available_filters(self) -> List[Dict[str, Any]]:
        """
        Get available filters matching admin panel logic.
        Each question becomes a filter, and for questions with options,
        we include their options in a hierarchical structure.
        """
        filters = [
            {
                'id': 'created_at',
                'name': 'Дата создания',
                'type': 'date'
            },
            {
                'id': 'updated_at',
                'name': 'Дата обновления',
                'type': 'date'
            },
            {
                'id': 'status',
                'name': 'Статус',
                'type': 'status',
                'choices': dict((key, str(value)) for key, value in SurveySubmission.Status.choices)
            }
        ]
        
        # Add question filters
        for question in self.questions:
            if question.input_type in ['single_choice', 'multiple_choice']:
                # Get all options for this question
                options = question.options.all()
                
                # Create choices dict with hierarchical structure
                choices = {}
                root_options = [opt for opt in options if not opt.parent_id]
                
                for root_opt in root_options:
                    # Get children for this root option
                    children = [opt for opt in options if opt.parent_id == root_opt.id]
                    
                    choices[str(root_opt.id)] = {
                        'text': root_opt.text,
                        'has_children': bool(children),
                        'children': {
                            str(child.id): child.text 
                            for child in children
                        }
                    }
                
                filters.append({
                    'id': str(question.id),
                    'name': str(question.field_type.title),
                    'type': 'choice',
                    'choices': choices,
                    'question_id': question.id
                })
            else:
                # Text question
                filters.append({
                    'id': str(question.id),
                    'name': str(question.field_type.title),
                    'type': 'text',
                    'question_id': question.id
                })
            
        return filters

    @sync_to_async
    def set_status_filter(self, status: str) -> None:
        """Set status filter."""
        self._status_filter = status 

    async def add_option_filter(self, question_id: int, option_id: str) -> None:
        """Add option filter for a question."""
        logger.debug(f"Adding option filter - question_id: {question_id}, option_id: {option_id}")
        
        # Get question and option
        question = await sync_to_async(Question.objects.get)(id=question_id)
        option = await sync_to_async(AnswerOption.objects.get)(id=option_id)
        
        # Create filter data
        filter_data = {
            'value': option.text,
            'question_id': question_id,
            'option_id': option_id
        }
        
        # Initialize list if not exists
        if str(question_id) not in self._response_filters_data:
            self._response_filters_data[str(question_id)] = []
            
        # Add to list if not already present
        if filter_data not in self._response_filters_data[str(question_id)]:
            self._response_filters_data[str(question_id)].append(filter_data)
            
        logger.debug(f"Added option filter: {filter_data}")
        logger.debug(f"Current response filters: {self._response_filters_data}") 