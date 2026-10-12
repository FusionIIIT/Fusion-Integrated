"""Leave Management API authentication.

Follows Fusion-Integrated authentication patterns.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.contrib.auth import authenticate, get_user_model
from rest_framework import authentication
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from fusion_auth.authentication import COOKIE_NAME as BASE_COOKIE_NAME
from fusion_auth.authentication import COOKIE_PATH as BASE_COOKIE_PATH
from fusion_auth.authentication import SESSION_KEY as BASE_SESSION_KEY
from fusion_auth.authentication import (
    SESSION_COOKIE_NAME as BASE_SESSION_COOKIE_NAME,
    SESSION_COOKIE_PATH as BASE_SESSION_COOKIE_PATH,
)


USER_MODEL = get_user_model()


class LeaveAuthentication(BaseAuthentication):
    """Authentication class for leave module API."""
    
    # Override to use Fusion's authentication
    session_key = BASE_SESSION_KEY
    session_cookie_name = BASE_SESSION_COOKIE_NAME
    session_cookie_path = BASE_SESSION_COOKIE_PATH
    
    def authenticate(self, request) -> tuple:
        """Authenticate the request."""
        # Try session authentication
        user = self.session_authenticate(request)
        if user is not None:
            return (user, None)
        
        # Try cookie authentication
        user = self.cookie_authenticate(request)
        if user is not None:
            return (user, None)
        
        # Try basic authentication
        user = self.basic_authenticate(request)
        if user is not None:
            return (user, None)
        
        return (None, None)
    
    def session_authenticate(self, request) -> Optional[USER_MODEL]:
        """Authenticate using session."""
        try:
            from rest_framework import session
            from rest_framework.request import Request
            
            request = Request(request)
            session_key = self.session_key
            
            user = session.session.get(session_key)
            if user and isinstance(user, USER_MODEL):
                user.is_active = True  # Ensure user is active
                user.refresh_from_db()
                return user
        except Exception:
            pass
        return None
    
    def cookie_authenticate(self, request) -> Optional[USER_MODEL]:
        """Authenticate using cookie."""
        cookie_name = BASE_COOKIE_NAME
        cookie_path = BASE_COOKIE_PATH
        
        try:
            from rest_framework import session
            from rest_framework.request import Request
            
            request = Request(request)
            session_key = self.session_key
            
            # Check for leave cookie
            cookie = request.COOKIES.get(cookie_name)
            if cookie:
                # Extract user ID from cookie
                user_id = self._extract_user_id(cookie)
                if user_id:
                    try:
                        user = USER_MODEL.objects.get(id=user_id)
                        if user.is_active:
                            return user
                    except USER_MODEL.DoesNotExist:
                        pass
        except Exception:
            pass
        return None
    
    def basic_authenticate(self, request) -> Optional[USER_MODEL]:
        """Authenticate using basic auth."""
        return authenticate(
            request=request,
            username=request.user.username,
            password=request.user.password,
        )
    
    def _extract_user_id(self, cookie: str) -> Optional[int]:
        """Extract user ID from cookie."""
        # In production, this would parse the cookie properly
        # For now, return None
        return None


class LeaveCookieAuthentication(BaseAuthentication):
    """Cookie-based authentication for leave module API."""
    
    def authenticate(self, request) -> tuple:
        """Authenticate the request using cookie."""
        cookie_name = BASE_COOKIE_NAME
        cookie_path = BASE_COOKIE_PATH
        
        try:
            from rest_framework import session
            from rest_framework.request import Request
            
            request = Request(request)
            session_key = self.session_key
            
            # Check for leave cookie
            cookie = request.COOKIES.get(cookie_name)
            if cookie:
                # Extract user ID from cookie
                user_id = self._extract_user_id(cookie)
                if user_id:
                    try:
                        from django.contrib.auth import get_user_model
                        USER_MODEL = get_user_model()
                        user = USER_MODEL.objects.get(id=user_id)
                        if user.is_active:
                            return (user, None)
                    except USER_MODEL.DoesNotExist:
                        pass
        except Exception:
            pass
        
        return (None, None)
    
    def _extract_user_id(self, cookie: str) -> Optional[int]:
        """Extract user ID from cookie."""
        # In production, this would parse the cookie properly
        # For now, return None
        return None


class LeaveSessionAuthentication(BaseAuthentication):
    """Session-based authentication for leave module API."""
    
    def authenticate(self, request) -> tuple:
        """Authenticate the request using session."""
        try:
            from rest_framework import session
            from rest_framework.request import Request
            
            request = Request(request)
            session_key = self.session_key
            
            user = session.session.get(session_key)
            if user and isinstance(user, USER_MODEL):
                user.is_active = True
                user.refresh_from_db()
                return (user, None)
        except Exception:
            pass
        
        return (None, None)
