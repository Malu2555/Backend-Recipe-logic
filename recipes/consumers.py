"""Consumers for recipe review WebSocket interactions.

This module provides a robust, asynchronous, class-based consumer to handle
real-time review creation, updates and deletions for a specific recipe.
Clients should connect to the URL pattern defined in `recipes.routing` (see
`ws/recipes/<recipe_id>/reviews/`).

Protocol (JSON messages):
- To subscribe and receive the initial review list, simply connect and send
  {"action": "list"} (or the server will send it on connect).
- To create a review: {"action": "create", "data": {"rating": 5, "comment": "Nice!", "user": "alice"}}
- To update a review: {"action": "update", "data": {"id": 12, "rating": 4, "comment": "Updated."}}
- To delete a review: {"action": "delete", "data": {"id": 12}}

Server broadcasts these events to the group:
- review_created
- review_updated
- review_deleted
- recipe_message (for recipe updates/deletions/creation events)

The consumer uses Django ORM via `database_sync_to_async` and validates
payloads using the existing `ReviewSerializer`.

@drf_spectacular.openapi.extend_schema documentation:
    Real-time WebSocket protocol for recipe reviews and cache invalidation events.
    
    WebSocket Operations:
    - connect: Subscribes to recipe review updates
    - disconnect: Unsubscribes from updates
    - receive_json: Handles client actions (create, update, delete, list)
    - review_created: Broadcast event when new review is created
    - review_updated: Broadcast event when review is updated
    - review_deleted: Broadcast event when review is deleted
    - recipe_message: Broadcast event for recipe-level changes (via signals)
    
    Event Flow:
    1. Client connects to ws/recipes/{recipe_id}/reviews/
    2. Consumer joins group: reviews_recipe_{recipe_id}
    3. Client sends action messages
    4. Django signals trigger cache invalidation
    5. recipe_message method broadcasts changes to all connected clients
    6. Consumer sends JSON response back to client
"""

import logging# for recording errors
from typing import Dict, Any # for adding type hints to your code making it  easier to catch errors
#allows you to specify that a variable is expected to be a dictionary with string keys and values of any type
#though python(it is dynamically-typed) does not enforce these types at runtime,it helps with code readability and static analysis tools

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async # wraps sync db calls for async use, preventing blocking the event loop(orm is sync)
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from .models import Review, Recipe
from .serializers import ReviewSerializer # to serialize/deserialize review data,only needed in this case

logger = logging.getLogger(__name__)


class ReviewConsumer(AsyncWebsocketConsumer):
    """Async WebSocket consumer for recipe reviews.

    URL should include `recipe_id` as a named URL kwarg (see `recipes.routing`).
    The consumer validates incoming payloads, persists changes to the DB,
    and broadcasts review events to other connected clients in the same
    recipe-specific group.
    """

    async def connect(self):# handling the initial websocket connection/handshake
        self.recipe_id = self.scope.get("url_route", {}).get("kwargs", {}).get("recipe_id")# specific recipe id from the url
        if not self.recipe_id:
            await self.close(code=4000)
            return

        self.group_name = f"reviews_recipe_{self.recipe_id}"

        # validate recipe exists
        try:
            await self.get_recipe(self.recipe_id)
        except ObjectDoesNotExist:
            await self.close(code=4001)
            return

        # join group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # send initial list of reviews
        await self.send_reviews_list()

    async def disconnect(self, close_code):#handling websocket disconnection
        # leave group
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:  # defensive
            logger.exception("Error discarding group on disconnect")

    async def receive_json(self, content: Dict[str, Any], **kwargs):# actual incoming message handler from clients/message handler
        """
        Handle incoming JSON messages. Expect an `action` key.
        
        @drf_spectacular.openapi.extend_schema documentation:
            operation_id: receive_json
            description: |
                Processes incoming WebSocket messages from clients.
                
                Supported Actions:
                - create: Create a new review for the recipe
                - list: Get all reviews for the recipe
                - update: Update an existing review
                - delete: Delete a review
                - recipe_refresh: Request fresh recipe data (triggers cache refresh)
                
                Message Format:
                    {
                        "action": "create|list|update|delete|recipe_refresh",
                        "data": {
                            ...action-specific fields...
                        }
                    }
                
                Response Format:
                    {
                        "action": "action_name",
                        "data": {...},
                        "error": null  // if successful
                    }
                    
                Error Handling:
                    - Invalid action: returns error_invalid_action
                    - Missing required fields: returns action_failed
                    - Database errors: returns with error details and logs exception
            
            logging: All actions are logged at INFO or ERROR level
        """
        action = content.get("action")
        data = content.get("data", {}) or {}

        if action == "create":
            await self.handle_create(data)
        elif action == "list":
            await self.send_reviews_list()
        elif action == "update":
            await self.handle_update(data)
        elif action == "delete":
            await self.handle_delete(data)
        elif action == "recipe_refresh":
            # Handle recipe data refresh request
            await self.handle_recipe_refresh(data)
        else:
            logger.warning(
                f"Unknown WebSocket action received: {action}",
                extra={'action': action, 'recipe_id': self.recipe_id},
            )
            await self.send_json({"error": "invalid_action", "message": f"Unknown action: {action}"})

    # ----- handlers -----definitions for each incoming action/event from clients/action handlers
    async def handle_create(self, payload: Dict[str, Any]):
        """
        Create a review for the connected recipe and broadcast it.
        
        @drf_spectacular.openapi.extend_schema documentation:
            operation_id: handle_create
            description: |
                Creates a new review in the database and broadcasts it to all
                connected clients in the recipe group.
                
                Required Fields:
                - rating: int (1-5, required)
                - comment: str (optional)
                - user: str (optional, uses authenticated user or "Anonymous")
                
                Response:
                    {
                        "action": "created",
                        "data": {serialized_review}
                    }
                
                Events Triggered:
                - Django signal: post_save on Review model
                - Cache invalidation: recipe_reviews_{recipe_id}
                - WebSocket broadcast: review.created to all clients in group
                
                Error Handling:
                    - Missing rating: ValueError raised, error_create_failed returned
                    - Invalid rating: ValueError raised, error_create_failed returned
                    - Database error: logged and error_create_failed returned
        """
        user = self._get_user_from_scope() or payload.get("user") or "Anonymous"
        try:
            rating = payload.get("rating")
            comment = payload.get("comment")

            if rating is None:
                raise ValueError("rating is required")
            rating = int(rating)
            if not (1 <= rating <= 5):
                raise ValueError("rating must be between 1 and 5")

            review_obj = await self.create_review(user=user, rating=rating, comment=comment)
            serialized = await self.serialize_review(review_obj)

            logger.info(
                f"Review created for recipe #{self.recipe_id}",
                extra={
                    'review_id': review_obj.id,
                    'recipe_id': self.recipe_id,
                    'user': user,
                    'rating': rating,
                }
            )

            # broadcast to group
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "review.created",
                    "review": serialized,
                },
            )

            # also echo back success to sender
            await self.send_json({"action": "created", "data": serialized})

        except Exception as exc:
            logger.exception(
                f"Error creating review for recipe #{self.recipe_id}: {str(exc)}",
                extra={'recipe_id': self.recipe_id, 'user': user},
            )
            await self.send_json({"error": "create_failed", "message": str(exc)})

    async def handle_update(self, payload: Dict[str, Any]):
        """
        Update an existing review (id must be provided).
        
        @drf_spectacular.openapi.extend_schema documentation:
            operation_id: handle_update
            description: |
                Updates fields in an existing review and broadcasts the change
                to all connected clients.
                
                Required Fields:
                - id: int (review ID to update, required)
                
                Optional Fields to Update:
                - rating: int (1-5)
                - comment: str
                
                Response:
                    {
                        "action": "updated",
                        "data": {serialized_updated_review}
                    }
                
                Events Triggered:
                - Django signal: post_save on Review model
                - Cache invalidation: recipe_reviews_{recipe_id}
                - WebSocket broadcast: review.updated to all clients in group
                
                Error Handling:
                    - Missing id: ValueError raised, error_update_failed returned
                    - Invalid rating: ValueError raised, error_update_failed returned
                    - No fields to update: ValueError raised, error_update_failed returned
                    - Database error: logged and error_update_failed returned
        """
        try:
            review_id = payload.get("id")
            if not review_id:
                raise ValueError("id is required for update")

            fields = {}
            if "rating" in payload:
                rating = int(payload.get("rating"))
                if not (1 <= rating <= 5):
                    raise ValueError("rating must be between 1 and 5")
                fields["rating"] = rating
            if "comment" in payload:
                fields["comment"] = payload.get("comment")

            if not fields:
                raise ValueError("no updatable fields provided")

            review_obj = await self.update_review(review_id, fields)
            serialized = await self.serialize_review(review_obj)

            logger.info(
                f"Review #{review_id} updated for recipe #{self.recipe_id}",
                extra={
                    'review_id': review_id,
                    'recipe_id': self.recipe_id,
                    'updated_fields': list(fields.keys()),
                }
            )

            await self.channel_layer.group_send(self.group_name, {"type": "review.updated", "review": serialized})
            await self.send_json({"action": "updated", "data": serialized})
        except Exception as exc:
            logger.exception(
                f"Error updating review #{payload.get('id')} for recipe #{self.recipe_id}: {str(exc)}",
                extra={'recipe_id': self.recipe_id, 'review_id': payload.get('id')},
            )
            await self.send_json({"error": "update_failed", "message": str(exc)})

    async def handle_delete(self, payload: Dict[str, Any]):
        """
        Delete a review with the given id.
        
        @drf_spectacular.openapi.extend_schema documentation:
            operation_id: handle_delete
            description: |
                Deletes a review from the database and broadcasts the deletion
                to all connected clients in the recipe group.
                
                Required Fields:
                - id: int (review ID to delete, required)
                
                Response:
                    {
                        "action": "deleted",
                        "data": {"id": review_id}
                    }
                
                Events Triggered:
                - Django signal: post_delete on Review model
                - Cache invalidation: recipe_reviews_{recipe_id}, recipe_avg_rating_{recipe_id}
                - WebSocket broadcast: review.deleted to all clients in group
                
                Error Handling:
                    - Missing id: ValueError raised, error_delete_failed returned
                    - Review not found: ValueError raised, error_delete_failed returned
                    - Database error: logged and error_delete_failed returned
        """
        try:
            review_id = payload.get("id")
            if not review_id:
                raise ValueError("id is required for delete")

            deleted = await self.delete_review(review_id)
            if not deleted:
                raise ValueError("review not found or not deleted")

            logger.warning(
                f"Review #{review_id} deleted for recipe #{self.recipe_id}",
                extra={'review_id': review_id, 'recipe_id': self.recipe_id},
            )

            await self.channel_layer.group_send(self.group_name, {"type": "review.deleted", "review": {"id": int(review_id)}})
            await self.send_json({"action": "deleted", "data": {"id": int(review_id)}})
        except Exception as exc:
            logger.exception(
                f"Error deleting review #{payload.get('id')} for recipe #{self.recipe_id}: {str(exc)}",
                extra={'recipe_id': self.recipe_id, 'review_id': payload.get('id')},
            )
            await self.send_json({"error": "delete_failed", "message": str(exc)})

    async def handle_recipe_refresh(self, payload: Dict[str, Any]):
        """
        Handle recipe data refresh request from client.
        
        This method allows clients to request a fresh fetch of recipe data,
        typically triggered after receiving a recipe_message event indicating
        cache invalidation.
        
        @drf_spectacular.openapi.extend_schema documentation:
            operation_id: handle_recipe_refresh
            description: |
                Handles client request to refresh recipe data after cache invalidation.
                
                This is typically called after the client receives a recipe_message
                event from the server indicating that the recipe cache has been
                invalidated (due to create, update, or delete operations).
                
                Payload:
                    {
                        "action": "recipe_refresh",
                        "data": {
                            "recipe_id": int (optional, defaults to current recipe)
                        }
                    }
                
                Response:
                    {
                        "action": "recipe_refreshed",
                        "data": {fresh_recipe_data}
                    }
                
                Events Triggered:
                - Database query: Fetches fresh recipe data
                - Logging: INFO level log of refresh request
                
                Error Handling:
                    - Recipe not found: ObjectDoesNotExist logged and error returned
                    - Database error: logged and error_refresh_failed returned
            
            triggers: Client action or automatic after recipe_message
            consequence: Returns fresh recipe data, bypassing cache
        """
        try:
            recipe_id = payload.get("recipe_id") or self.recipe_id
            
            logger.info(
                f"Recipe refresh requested",
                extra={'recipe_id': recipe_id, 'requested_by': self.recipe_id},
            )
            
            recipe = await self.get_recipe(recipe_id)
            
            # You can create a method to serialize recipe data
            # For now, we'll send basic recipe info
            recipe_data = {
                'id': recipe.id,
                'title': recipe.title,
                'description': recipe.description,
                'created_at': str(recipe.created_at),
                'updated_at': str(recipe.created_at),  # Adjust based on your model
                'author_id': recipe.author_id,
                'is_official': recipe.is_official,
            }
            
            logger.info(
                f"Recipe data refreshed and sent to client",
                extra={'recipe_id': recipe_id},
            )
            
            await self.send_json({
                "action": "recipe_refreshed",
                "data": recipe_data,
                "message": "Recipe data refreshed from database",
            })
            
        except ObjectDoesNotExist:
            logger.warning(
                f"Recipe refresh failed: recipe not found",
                extra={'recipe_id': payload.get('recipe_id')},
            )
            await self.send_json({
                "error": "recipe_not_found",
                "message": f"Recipe {payload.get('recipe_id')} not found",
            })
        except Exception as exc:
            logger.exception(
                f"Error refreshing recipe data: {str(exc)}",
                extra={'recipe_id': self.recipe_id},
            )
            await self.send_json({
                "error": "refresh_failed",
                "message": f"Failed to refresh recipe data: {str(exc)}",
            })

    # ----- group event handlers -----this is a signaling mechanism to broadcast events to all clients in the same group
    #other clients will receive these events when a review is created/updated/deleted
    async def review_created(self, event):
        await self.send_json({"action": "review_created", "data": event.get("review")})

    async def review_updated(self, event):
        await self.send_json({"action": "review_updated", "data": event.get("review")})

    async def review_deleted(self, event):
        await self.send_json({"action": "review_deleted", "data": event.get("review")})

    async def recipe_message(self, event):
        """
        Handler for recipe-level changes triggered by Django signals.
        
        This method handles messages sent from the signals module when recipes
        are created, updated, or deleted. It processes the cache invalidation
        event and broadcasts it to all connected clients in the recipe group.
        
        @drf_spectacular.openapi.extend_schema documentation:
            operation_id: recipe_message
            description: |
                Handles recipe-level changes that trigger cache invalidation.
                
                This method is triggered by Django signals (post_save, post_delete)
                from the recipes.signals module and broadcasts updates to all
                WebSocket clients connected to this recipe's group.
                
                Message Type: recipe.message
                Source: Django Signals (signals.py)
                
                Event Types:
                - recipe_created: New recipe added to system
                - recipe_updated: Existing recipe modified
                - recipe_deleted: Recipe removed from system
                
                Event Payload:
                    {
                        "action": "recipe_message",
                        "event_type": "recipe_created|recipe_updated|recipe_deleted",
                        "data": {
                            "recipe_id": int,
                            "recipe_title": str,
                            "author_id": int,
                            "action": str,
                            "timestamp": datetime,
                            "keys_invalidated": int (number of cache keys cleared)
                        }
                    }
                
                Consequence: 
                - Clients receive notification of cache invalidation
                - Clients should refetch recipe data from API
                - Cache in Redis is cleared, forcing fresh database queries
                
                Logging:
                - INFO level: Recipe cache invalidation events
                - DEBUG level: Individual cache key invalidations
                - ERROR level: Exceptions during cache clearing
            
            triggers: Django Signals
                - recipes.signals.invalidate_recipe_cache_on_save (POST, PUT, PATCH)
                - recipes.signals.invalidate_recipe_cache_on_delete (DELETE)
                
            group_send_type: 'recipe.message'
        """
        try:
            event_type = event.get("event_type", "unknown")
            recipe_data = event.get("data", {})
            
            # Log the recipe_message event
            logger.info(
                f"Recipe message broadcasted: {event_type}",
                extra={
                    'event_type': event_type,
                    'recipe_id': recipe_data.get('recipe_id'),
                    'recipe_title': recipe_data.get('recipe_title'),
                    'keys_invalidated': recipe_data.get('keys_invalidated'),
                }
            )
            
            # Send the recipe message to the WebSocket client
            await self.send_json({
                "action": "recipe_message",
                "event_type": event_type,
                "data": recipe_data,
                "message": f"Recipe cache invalidated due to {event_type}",
            })
            
        except Exception as exc:
            logger.exception(
                f"Error handling recipe_message event: {str(exc)}",
                extra={'event': event},
            )
            # Notify client of the error gracefully
            await self.send_json({
                "error": "recipe_message_error",
                "message": f"Failed to process recipe update: {str(exc)}",
            })

    # ----- helpers (DB operations) -----
    async def send_reviews_list(self):
        reviews = await self.get_reviews_for_recipe(self.recipe_id)
        serialized = ReviewSerializer(reviews, many=True).data# serialize the list of reviews (str to json,json to object/model instance)
        await self.send_json({"action": "list", "data": serialized})

    def _get_user_from_scope(self):# extract user info from the connection scope
        user = self.scope.get("user")
        try:
            if user and getattr(user, "is_authenticated", False):
                # prefer username when available
                return getattr(user, "username", str(user))
        except Exception:
            pass
        return None
    # ----- database operations -----or the actual actions from clients that interact with the database e.g create/update/delete/fetch reviews

    @database_sync_to_async #handles sync db calls in async context/prevents blocking the event loop
    def get_recipe(self, recipe_id: int) -> Recipe:#get the recipe object by id/fetch recipe from db
        return Recipe.objects.get(pk=recipe_id)

    @database_sync_to_async
    def get_reviews_for_recipe(self, recipe_id: int):
        return list(Review.objects.filter(recipe_id=recipe_id).order_by("created_at"))# get all reviews by recipe id,ordered by create time

    @database_sync_to_async
    def create_review(self, user: str, rating: int, comment: str) -> Review:# the actual creation of a review in the db
        recipe = Recipe.objects.get(pk=self.recipe_id)#get the recipe object
        return Review.objects.create(recipe=recipe, user=user, rating=rating, comment=comment, created_at=timezone.now())

    @database_sync_to_async
    def serialize_review(self, review: Review):# for review transformation and validation using the existing serializer
        return ReviewSerializer(review).data

    @database_sync_to_async
    def update_review(self, review_id: int, fields: Dict[str, Any]) -> Review:# the -> is a type hint indicating the return type of the function
        #str keys and any type values dictionary
        review = Review.objects.get(pk=review_id, recipe_id=self.recipe_id)
        for key, value in fields.items():#k for key,v for value
            setattr(review, key, value)
        review.save()
        return review

    @database_sync_to_async
    def delete_review(self, review_id: int) -> bool:# if a user wants to delete a review
        deleted, _ = Review.objects.filter(pk=review_id, recipe_id=self.recipe_id).delete()
        return bool(deleted)
