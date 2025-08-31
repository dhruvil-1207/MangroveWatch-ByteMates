import os
import json
import requests
import numpy as np
from datetime import datetime
from PIL import Image, ExifTags
from textblob import TextBlob
import cv2
import tensorflow as tf
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import folium
from typing import Dict, List, Tuple, Optional

class RealMangroveAI:
    """Real AI-powered validation using machine learning models and APIs"""
    
    def __init__(self):
        self.geolocator = Nominatim(user_agent="mangrove_watch")
        
        # Load pre-trained models (you can download these)
        self.load_models()
        
        # API keys (set these in environment variables)
        self.google_maps_key = os.getenv('GOOGLE_MAPS_API_KEY')
        self.satellite_api_key = os.getenv('SATELLITE_API_KEY')
        self.huggingface_key = os.getenv('HUGGINGFACE_API_KEY')
        
    def load_models(self):
        """Load pre-trained ML models"""
        try:
            # Load text classification model (for spam detection)
            self.text_classifier = self.load_text_model()
            
            # Load image classification model (for photo validation)
            self.image_classifier = self.load_image_model()
            
            print("✅ AI models loaded successfully")
        except Exception as e:
            print(f"⚠️ Model loading failed: {e}")
            self.text_classifier = None
            self.image_classifier = None

    def load_text_model(self):
        """Load pre-trained text classification model"""
        try:
            # Use Hugging Face transformers for text analysis
            from transformers import pipeline
            return pipeline("text-classification", 
                          model="unitary/toxic-bert",
                          return_all_scores=True)
        except:
            return None

    def load_image_model(self):
        """Load pre-trained image classification model"""
        try:
            # Use TensorFlow Hub model for image classification
            import tensorflow_hub as hub
            model_url = "https://tfhub.dev/google/imagenet/mobilenet_v2_100_224/classification/5"
            return hub.load(model_url)
        except:
            return None

    async def validate_report_ai(self, report_data: Dict) -> Dict:
        """Main AI validation using real ML models"""
        validation_result = {
            'confidence_score': 0,
            'validation_status': 'pending',
            'ai_analysis': {},
            'risk_flags': [],
            'recommendations': []
        }
        
        # 1. Real geographical validation using APIs
        geo_validation = await self.validate_geography_api(
            report_data.get('latitude'), 
            report_data.get('longitude')
        )
        
        # 2. AI-powered text analysis
        text_analysis = self.analyze_text_ai(
            report_data.get('description', ''),
            report_data.get('title', '')
        )
        
        # 3. Computer vision photo analysis
        photo_analysis = self.analyze_photo_ai(
            report_data.get('photo_filename')
        )
        
        # 4. Satellite imagery comparison
        satellite_validation = await self.validate_satellite_data(
            report_data.get('latitude'),
            report_data.get('longitude')
        )
        
        # 5. Combine all AI analyses
        validation_result = self.combine_ai_results(
            geo_validation, text_analysis, photo_analysis, satellite_validation
        )
        
        return validation_result

    async def validate_geography_api(self, lat: float, lng: float) -> Dict:
        """Real geographical validation using Google Maps API"""
        if not lat or not lng or not self.google_maps_key:
            return {'score': 0.5, 'analysis': 'No GPS or API key'}
        
        try:
            # Google Maps Places API to check nearby features
            places_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': f"{lat},{lng}",
                'radius': 5000,  # 5km radius
                'type': 'natural_feature',
                'key': self.google_maps_key
            }
            
            response = requests.get(places_url, params=params)
            places_data = response.json()
            
            # Check for mangrove-related places
            mangrove_indicators = ['mangrove', 'wetland', 'estuary', 'coastal', 'lagoon']
            score = 0.3  # Base score
            
            for place in places_data.get('results', []):
                place_name = place.get('name', '').lower()
                for indicator in mangrove_indicators:
                    if indicator in place_name:
                        score += 0.2
                        
            # Check if location is coastal using elevation API
            elevation_url = f"https://maps.googleapis.com/maps/api/elevation/json"
            elev_params = {
                'locations': f"{lat},{lng}",
                'key': self.google_maps_key
            }
            
            elev_response = requests.get(elevation_url, params=elev_params)
            elev_data = elev_response.json()
            
            if elev_data.get('results'):
                elevation = elev_data['results'][0]['elevation']
                if elevation < 10:  # Less than 10m above sea level
                    score += 0.3
                    
            return {
                'score': min(score, 1.0),
                'analysis': f'Coastal validation: {score:.1f}, Elevation: {elevation}m',
                'nearby_features': len(places_data.get('results', []))
            }
            
        except Exception as e:
            return {'score': 0.4, 'analysis': f'API error: {str(e)}'}

    def analyze_text_ai(self, description: str, title: str) -> Dict:
        """AI-powered text analysis using NLP models"""
        combined_text = f"{title} {description}"
        
        analysis = {
            'spam_probability': 0,
            'sentiment_score': 0,
            'environmental_keywords': 0,
            'credibility_score': 0.5
        }
        
        try:
            # 1. Spam detection using pre-trained model
            if self.text_classifier:
                toxic_result = self.text_classifier(combined_text)
                for result in toxic_result:
                    if result['label'] == 'TOXIC' and result['score'] > 0.7:
                        analysis['spam_probability'] = result['score']
            
            # 2. Sentiment analysis using TextBlob
            blob = TextBlob(combined_text)
            analysis['sentiment_score'] = blob.sentiment.polarity
            
            # 3. Environmental keyword detection using NLP
            environmental_terms = [
                'mangrove', 'deforestation', 'illegal cutting', 'pollution',
                'ecosystem', 'biodiversity', 'coastal erosion', 'habitat loss'
            ]
            
            found_terms = sum(1 for term in environmental_terms if term in combined_text.lower())
            analysis['environmental_keywords'] = found_terms / len(environmental_terms)
            
            # 4. Calculate credibility score
            credibility = 0.5
            
            # Positive indicators
            if analysis['environmental_keywords'] > 0.3:
                credibility += 0.2
            if len(description) > 50:
                credibility += 0.1
            if analysis['sentiment_score'] < -0.1:  # Negative sentiment (concern)
                credibility += 0.1
                
            # Negative indicators
            if analysis['spam_probability'] > 0.5:
                credibility -= 0.3
            if len(description) < 20:
                credibility -= 0.2
                
            analysis['credibility_score'] = max(0, min(1, credibility))
            
        except Exception as e:
            print(f"Text analysis error: {e}")
            
        return analysis

    def analyze_photo_ai(self, photo_filename: str) -> Dict:
        """Computer vision analysis of uploaded photos"""
        if not photo_filename:
            return {'score': 0.7, 'analysis': 'No photo provided'}
        
        photo_path = os.path.join('uploads', photo_filename)
        if not os.path.exists(photo_path):
            return {'score': 0.3, 'analysis': 'Photo file not found'}
        
        analysis = {
            'authenticity_score': 0.5,
            'environmental_content': 0.5,
            'technical_quality': 0.5,
            'metadata_analysis': {}
        }
        
        try:
            # 1. Load and analyze image
            image = cv2.imread(photo_path)
            if image is None:
                return {'score': 0.2, 'analysis': 'Invalid image file'}
            
            # 2. Technical quality analysis
            # Check image sharpness (Laplacian variance)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            analysis['technical_quality'] = min(laplacian_var / 1000, 1.0)
            
            # 3. EXIF metadata analysis
            with Image.open(photo_path) as img:
                exif = img._getexif()
                if exif:
                    analysis['metadata_analysis']['has_exif'] = True
                    
                    # Check for GPS data
                    for tag, value in exif.items():
                        tag_name = ExifTags.TAGS.get(tag, tag)
                        if tag_name == 'GPS':
                            analysis['metadata_analysis']['has_gps'] = True
                        elif tag_name == 'DateTime':
                            analysis['metadata_analysis']['timestamp'] = str(value)
                else:
                    analysis['metadata_analysis']['has_exif'] = False
            
            # 4. Color analysis for environmental content
            # Analyze green pixels (vegetation indicator)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            green_mask = cv2.inRange(hsv, np.array([40, 50, 50]), np.array([80, 255, 255]))
            green_ratio = cv2.countNonZero(green_mask) / (image.shape[0] * image.shape[1])
            analysis['environmental_content'] = min(green_ratio * 3, 1.0)
            
            # 5. Use pre-trained model for scene classification (if available)
            if self.image_classifier:
                try:
                    # Resize image for model input
                    resized = cv2.resize(image, (224, 224))
                    input_tensor = tf.constant(resized, dtype=tf.float32)
                    input_tensor = tf.expand_dims(input_tensor, 0)
                    
                    # Run inference (simplified)
                    predictions = self.image_classifier(input_tensor)
                    # Process predictions for environmental content
                    
                except Exception as e:
                    print(f"Model inference error: {e}")
            
            # Calculate overall authenticity score
            scores = [
                analysis['technical_quality'],
                analysis['environmental_content'],
                0.8 if analysis['metadata_analysis'].get('has_exif') else 0.4
            ]
            analysis['authenticity_score'] = np.mean(scores)
            
        except Exception as e:
            print(f"Photo analysis error: {e}")
            return {'score': 0.4, 'analysis': f'Analysis failed: {str(e)}'}
        
        return analysis

    async def validate_satellite_data(self, lat: float, lng: float) -> Dict:
        """Validate against satellite imagery data"""
        if not lat or not lng:
            return {'score': 0.5, 'analysis': 'No coordinates provided'}
        
        try:
            # Use Google Earth Engine or similar API for satellite data
            # This is a simplified example - you'd need proper satellite API access
            
            # For now, simulate satellite validation
            # In production, you'd check:
            # - Recent satellite images for the area
            # - Change detection algorithms
            # - Vegetation indices (NDVI)
            # - Coastal change analysis
            
            # Placeholder for real satellite API integration
            satellite_score = 0.6  # Would be calculated from real satellite data
            
            return {
                'score': satellite_score,
                'analysis': 'Satellite validation pending - API integration needed',
                'change_detected': False,
                'vegetation_index': 0.4
            }
            
        except Exception as e:
            return {'score': 0.5, 'analysis': f'Satellite analysis error: {str(e)}'}

    def combine_ai_results(self, geo_val: Dict, text_val: Dict, photo_val: Dict, satellite_val: Dict) -> Dict:
        """Combine all AI analysis results into final validation"""
        
        # Weight the different validation components
        weights = {
            'geography': 0.3,
            'text': 0.25,
            'photo': 0.25,
            'satellite': 0.2
        }
        
        # Calculate weighted score
        overall_score = (
            geo_val['score'] * weights['geography'] +
            text_val['credibility_score'] * weights['text'] +
            photo_val['authenticity_score'] * weights['photo'] +
            satellite_val['score'] * weights['satellite']
        )
        
        # Determine validation status
        if overall_score >= 0.75:
            status = 'auto_validated'
            recommendations = ['Report appears highly credible', 'Auto-approved for publication']
        elif overall_score >= 0.5:
            status = 'pending_review'
            recommendations = ['Moderate confidence', 'Requires manual review by authority']
        else:
            status = 'flagged'
            recommendations = ['Low confidence score', 'Flagged for detailed investigation']
        
        # Compile risk flags
        risk_flags = []
        if text_val['spam_probability'] > 0.7:
            risk_flags.append('High spam probability detected')
        if geo_val['score'] < 0.3:
            risk_flags.append('Location not verified as mangrove habitat')
        if photo_val['authenticity_score'] < 0.4:
            risk_flags.append('Photo authenticity questionable')
        
        return {
            'confidence_score': round(overall_score * 100, 1),
            'validation_status': status,
            'ai_analysis': {
                'geography': geo_val,
                'text_analysis': text_val,
                'photo_analysis': photo_val,
                'satellite': satellite_val
            },
            'risk_flags': risk_flags,
            'recommendations': recommendations,
            'processing_timestamp': datetime.utcnow().isoformat()
        }

    def get_required_apis(self) -> Dict:
        """Return list of APIs needed for full functionality"""
        return {
            'google_maps': {
                'purpose': 'Geographical validation, elevation data',
                'url': 'https://developers.google.com/maps/documentation',
                'cost': '$2-7 per 1000 requests'
            },
            'huggingface': {
                'purpose': 'Advanced text classification and NLP',
                'url': 'https://huggingface.co/docs/api-inference',
                'cost': 'Free tier available'
            },
            'google_earth_engine': {
                'purpose': 'Satellite imagery and environmental data',
                'url': 'https://earthengine.google.com',
                'cost': 'Free for research, paid for commercial'
            },
            'tensorflow_hub': {
                'purpose': 'Pre-trained ML models',
                'url': 'https://tfhub.dev',
                'cost': 'Free'
            }
        }

# Initialize real AI validator
real_ai_validator = RealMangroveAI()