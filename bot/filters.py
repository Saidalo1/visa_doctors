"""Filter manager for survey submissions."""
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

from asgiref.sync import sync_to_async
from django.db.models import Q, Prefetch
from django.utils import timezone

from app.models import SurveySubmission, Question, Response

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

# Add formatter to file handler
file_handler.setFormatter(formatter)

# Remove any existing handlers and add file handler
logger.handlers = []
logger.addHandler(file_handler)

# Add minimal console output for critical errors only
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.CRITICAL)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class SurveyFilter:
    """Filter manager for survey submissions."""
    
    def __init__(self, state: Dict[str, Any] = None):
        """Initialize filter manager."""
        logger.debug(f"Initializing SurveyFilter with state: {state}")
        
        if state is None:
            state = {
                'date_filters': {},
                'response_filters': {},
                'selected_dates': set(),
                'status_filter': None
            }
        
        self.date_filters = state.get('date_filters', {})
        self.response_filters = {}  # Will be populated from response_filters_data
        self._response_filters_data = state.get('response_filters', {})  # Store IDs instead of objects
        self.selected_dates = set(state.get('selected_dates', set()))  # Store selected dates
        self._questions = None  # Lazy load questions
        self._status_filter = state.get('status_filter')  # Store status filter
        
        logger.debug(f"Initialized with date_filters: {self.date_filters}")
        logger.debug(f"Initialized with selected_dates: {self.selected_dates}")
        
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
        for question_id, data in self._response_filters_data.items():
            try:
                question = Question.objects.get(id=data['question_id'])
                active_filters.append({
                    'name': question.field_type.title,
                    'value': data['value']
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
        logger.debug(f"Before adding - date_filters: {self.date_filters}")
        
        try:
            question = Question.objects.get(id=question_id)
            self._response_filters_data[str(question_id)] = {
                'value': value,
                'question_id': question_id
            }
            self.response_filters[question] = value
            
            logger.debug(f"After adding - date_filters: {self.date_filters}")
            logger.debug(f"Response filters data: {self._response_filters_data}")
            
        except Question.DoesNotExist:
            logger.error(f"Question {question_id} not found")
            pass
            
    @sync_to_async
    def get_filtered_submissions(self) -> List[SurveySubmission]:
        """Get filtered submissions based on current filters."""
        queryset = SurveySubmission.objects.all()

        # Apply status filter
        if hasattr(self, '_status_filter') and self._status_filter:
            queryset = queryset.filter(status=self._status_filter)

        # Apply date filters
        for field, value in self.date_filters.items():
            # Convert string date to timezone-aware datetime
            date = timezone.make_aware(datetime.strptime(value, "%Y-%m-%d"))
            queryset = queryset.filter(**{field: date})

        # Apply response filters
        for question_id, filter_value in self._response_filters_data.items():
            responses = Response.objects.filter(question_id=question_id)
            
            # For text answers
            text_responses = responses.filter(text_answer__icontains=filter_value['value'])
            text_submission_ids = text_responses.values_list('submission_id', flat=True)
            
            # For selected options
            option_responses = responses.filter(selected_options__text__icontains=filter_value['value'])
            option_submission_ids = option_responses.values_list('submission_id', flat=True)
            
            # Combine IDs from both types of responses
            matching_submission_ids = list(text_submission_ids) + list(option_submission_ids)
            if matching_submission_ids:
                queryset = queryset.filter(id__in=matching_submission_ids)
            else:
                return SurveySubmission.objects.none()  # Return empty queryset if no matches

        # Prefetch related data for efficiency
        queryset = queryset.prefetch_related(
            'responses__question',
            'responses__selected_options'
        )

        return queryset.distinct()
        
    @sync_to_async
    def get_available_filters(self) -> List[Dict[str, Any]]:
        """
        Get available filters.
        
        Returns:
            List of available filters with their types
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
            filters.append({
                'id': str(question.id),
                'name': question.field_type.title,
                'type': 'text',
                'question_id': question.id
            })
            
        return filters 

    @sync_to_async
    def set_status_filter(self, status: str) -> None:
        """Set status filter."""
        self._status_filter = status 