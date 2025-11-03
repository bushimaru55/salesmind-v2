from django.db import models
from django.contrib.auth.models import User
import uuid


class Session(models.Model):
    STATUS_CHOICES = [
        ('pending', '開始前'),
        ('active', '進行中'),
        ('finished', '完了'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    industry = models.CharField(max_length=100)
    value_proposition = models.TextField()
    customer_persona = models.TextField(null=True, blank=True)
    customer_pain = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Session {self.id} - {self.industry}"


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('salesperson', '営業担当者'),
        ('customer', 'AI顧客'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    message = models.TextField()
    sequence = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['session', 'sequence']
        indexes = [
            models.Index(fields=['session', 'sequence']),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.message[:50]}..."


class Report(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name='report')
    spin_scores = models.JSONField()
    feedback = models.TextField()
    next_actions = models.TextField()
    scoring_details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report for Session {self.session.id}"

