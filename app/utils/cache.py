"""Utilities for cache operations."""
from typing import Type, List, Union

from django.db.models import Model
from cacheops import invalidate_model, invalidate_obj


def invalidate_models(models: List[Type[Model]]) -> None:
    """
    Invalidate cache for multiple models at once.
    
    Args:
        models: List of model classes to invalidate cache for
    """
    for model in models:
        invalidate_model(model)


def invalidate_objects(objects: List[Model]) -> None:
    """
    Invalidate cache for multiple model instances at once.
    
    Args:
        objects: List of model instances to invalidate cache for
    """
    for obj in objects:
        invalidate_obj(obj)


def invalidate_app_models(app_label: str = 'app') -> None:
    """
    Invalidate cache for all models in an app.
    
    Args:
        app_label: App label to invalidate models for, defaults to 'app'
    """
    from django.apps import apps
    
    models = apps.get_app_config(app_label).get_models()
    invalidate_models(models)
