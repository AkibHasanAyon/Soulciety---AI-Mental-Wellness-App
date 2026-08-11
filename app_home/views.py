from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from notifications.helpers import send_push_notification_task
from datetime import timedelta
from .models import Quote, MoodEntry, DailyMove, ContentPost, Product, TabathaPrompt, TabathaDailyMessage
from .serializers import (
    QuoteSerializer, MoodEntrySerializer, DailyMoveSerializer,
    ContentPostSerializer, ProductSerializer
)

# home/views.py
from google import genai
from google.genai import types
from django.conf import settings
from django.utils import timezone

client = genai.Client(api_key=settings.GEMINI_API_KEY)


# home/views.py
from django.utils import timezone
from .models import GeneratedQuote # Import your new model

class DailyQuoteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        
        # 1. Get current mood
        current_mood = None
        if hasattr(user, 'profile') and user.profile.current_mood:
            current_mood = user.profile.current_mood
        
        # 2. Check Database first (The Cache)
        # We check if this user already has a quote for TODAY and this MOOD
        existing_quote = GeneratedQuote.objects.filter(
            user=user, 
            created_at=today, 
            mood=current_mood
        ).first()

        if existing_quote:
            return Response({
                "text": existing_quote.text,
                "author": "Soulciety AI",
                "personalized": True,
                "based_on_mood": existing_quote.mood,
                "cached": True # Optional flag for debugging
            })

        # 3. If no existing quote, proceed to Gemini
        mood_prompts = {
            'happy': "joyful, grateful, and full of light",
            'neutral': "calm, balanced, and present",
            'sad': "in need of comfort, healing, and gentle hope",
            'angry': "seeking peace, release, and inner calm",
            'calm': "deeply peaceful, centered, and serene",
        }
        mood_description = mood_prompts.get(current_mood or "neutral", "on a spiritual journey today")

        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash", # Use 3.5-flash for stability in 2026
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are a wise spiritual friend. Generate one short, beautiful, "
                        "uplifting quote (max 2 sentences). Do not include quotation marks."
                    ),
                    temperature=0.9,
                ),
                contents=f"Generate a quote for someone who is feeling {mood_description}."
            )

            quote_text = response.text.strip()
            if not quote_text:
                raise ValueError("Empty response")

            # 4. SAVE the generated quote so we don't call Gemini again today
            GeneratedQuote.objects.create(
                user=user,
                text=quote_text,
                mood=current_mood
            )

            return Response({
                "text": quote_text,
                "author": "Soulciety AI",
                "personalized": True,
                "based_on_mood": current_mood,
                "cached": False
            })

        except Exception as e:
            print(f"Gemini API error: {e}")
            # Fallback to static quotes
            quote = Quote.objects.filter(is_active=True).order_by('?').first()
            return Response(QuoteSerializer(quote).data if quote else {
                "text": "Every new day is a chance to align with your highest self.",
                "author": "Soulciety AI"
            })



    
# app_home/views.py (MoodCheckInView)
class MoodCheckInView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MoodEntrySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            mood_entry = serializer.save()  # Saves to MoodEntry

            # No need to update profile.current_mood — it's a property now!

            return Response({
                "message": "Mood recorded successfully",
                "current_mood": mood_entry.get_mood_display()
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)   

class DailyMoveView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        today = timezone.now().date()
        move = DailyMove.objects.filter(date=today).first()
        if not move:
            # Fallback: latest one
            move = DailyMove.objects.order_by('-date').first()
        if move:
            serializer = DailyMoveSerializer(move)
            return Response(serializer.data)
        return Response({"message": "No daily move today"}, status=status.HTTP_404_NOT_FOUND)

class PopularContentView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # Return 5 latest or most liked posts
        posts = ContentPost.objects.filter(is_featured=True).order_by('-created_at')[:5]
        serializer = ContentPostSerializer(posts, many=True)
        return Response(serializer.data)






# app_home/views.py

class FeaturedProductsView(APIView):
    permission_classes = [AllowAny] # Anyone can see the products

    def get(self, request):
        # Admin marks products as 'featured' in the dashboard
        products = Product.objects.filter(
            is_active=True, 
            is_featured=True
        ).order_by('-created_at')[:6]
        
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)











class HomeDataView(APIView):
    permission_classes = [IsAuthenticated]  # Now personalized

    def get_tabatha_message(self, today_date):
        daily_msg = TabathaDailyMessage.objects.filter(date=today_date).first()
        if daily_msg:
            return daily_msg.message
            
        active_prompt = TabathaPrompt.objects.filter(is_active=True).first()
        prompt_text = active_prompt.text if active_prompt else "You are Tabatha, founder of The Happy Soul Society. Generate a short, single-paragraph daily message (2-4 sentences max) to ground the user and invite them to step into their highest identity today. Speak casually."
        
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=prompt_text,
                    temperature=0.8,
                ),
                contents="Generate today's global message from Tabatha for all the Soulciety app users."
            )
            message_text = response.text.strip()
            if message_text:
                TabathaDailyMessage.objects.create(date=today_date, message=message_text)
                return message_text
        except Exception as e:
            print(f"Gemini API error for Tabatha Message: {e}")
            
        return "Quiet the mind and trust the unfolding of your beautiful journey."

    def get(self, request):
        today = timezone.now().date()

        # Let DailyQuoteView handle AI quote
        quote_view = DailyQuoteView()
        quote_view.request = request
        quote_response = quote_view.get(request)
        daily_quote = quote_response.data

        data = {
            "tabatha_message": self.get_tabatha_message(today),
            "daily_quote": daily_quote,
            "daily_move": DailyMoveSerializer(
                DailyMove.objects.filter(date=today).first() or 
                DailyMove.objects.order_by('-date').first()
            ).data if DailyMove.objects.exists() else None,
            
            "popular_content": ContentPostSerializer(
                ContentPost.objects.filter(is_featured=True).order_by('-created_at')[:5],
                many=True
            ).data,
            
            "featured_products": ProductSerializer(
                Product.objects.filter(is_active=True)[:6],
                many=True
            ).data,
        }
        return Response(data)
    
    
    
# class DailyQuoteView(APIView):
#     permission_classes = [IsAuthenticated]  # Now requires login to get personalized quote

#     def get(self, request):
#         user = request.user
#         current_mood = None

#         # Get user's current mood from profile
#         if hasattr(user, 'profile') and user.profile.current_mood:
#             current_mood = user.profile.current_mood
#         else:
#             current_mood = None

#         # Map mood keys to friendly prompts
#         mood_prompts = {
#             'happy': "joyful, grateful, and full of light",
#             'neutral': "calm, balanced, and present",
#             'sad': "in need of comfort, healing, and gentle hope",
#             'angry': "seeking peace, release, and inner calm",
#             'calm': "deeply peaceful, centered, and serene",
#         }

#         mood_description = mood_prompts.get(current_mood or "neutral", "on a spiritual journey today")
#         # 3. Generate quote via Gemini AI
#         try:
#             response = client.models.generate_content(
#                 model="gemini-3-flash-preview",
#                 config=types.GenerateContentConfig(
#                     system_instruction=(
#                         "You are a wise spiritual friend. Generate one short, beautiful, "
#                         "uplifting quote (max 2 sentences). Do not include quotation marks "
#                         "or author names. Speak directly to the heart."
#                     ),
#                     temperature=0.9,
#                     max_output_tokens=150,
#                 ),
#                 # We pass the specific mood context as the prompt content
#                 contents=f"Generate a quote for someone who is feeling {mood_description}."
#             )

#             # 4. Extract text safely
#             if not response.text:
#                 raise ValueError("Empty response from AI")

#             quote_text = response.text.strip()

#             # Fallback if AI fails
#             if not quote_text:
#                 quote_text = "Take a deep breath — the universe is always guiding you back to yourself."

#             return Response({
#                 "text": quote_text,
#                 "author": "Soulciety AI",
#                 "personalized": True,
#                 "based_on_mood": current_mood
#             })

#         except Exception as e:
#             print(f"Gemini API error: {e}")
#             # Graceful fallback to random static quote
#             quote = Quote.objects.filter(is_active=True).order_by('?').first()
#             if quote:
#                 return Response(QuoteSerializer(quote).data)
#             return Response({
#                 "text": "Every new day is a chance to align with your highest self.",
#                 "author": "Soulciety"
#             }, status=status.HTTP_200_OK)
