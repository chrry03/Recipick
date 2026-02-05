# 프론트엔드에서 받은 JSON 데이터를 모델에 넣고, 모델 데이터를 JSON으로 바꿔주는 번역기.
# "Flat 구조(프로필 정보를 유저 정보처럼 한 번에 수정)" 로직을 여기서 짜야함.
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['cooking_level', 'allergies', 'banned_ingredients']

class UserSerializer(serializers.ModelSerializer):
    # 1. 프로필 정보도 같이 보여주기 위해 연결
    profile = UserProfileSerializer(read_only=True) 
    
    # 2. 입력받을 때 Flat하게 받기 위한 필드 정의 (write_only)
    cooking_level = serializers.CharField(write_only=True, required=False)
    allergies = serializers.JSONField(write_only=True, required=False)
    banned_ingredients = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'nickname', 'profile',  # 조회 시 나갈 데이터
            'cooking_level', 'allergies', 'banned_ingredients' # 수정 시 들어올 데이터
        ]
        read_only_fields = ['email'] # 이메일은 수정 불가

    # ★ 핵심: PATCH 요청 시 Flat한 데이터를 Profile 모델에 넣어주는 로직
    def update(self, instance, validated_data):
        # 1. Body에서 프로필 관련 데이터만 쏙 뽑아냄
        cooking_level = validated_data.pop('cooking_level', None)
        allergies = validated_data.pop('allergies', None)
        banned_ingredients = validated_data.pop('banned_ingredients', None)

        # 2. User 모델 (닉네임 등) 업데이트
        instance = super().update(instance, validated_data)

        # 3. UserProfile 모델 업데이트
        # (프로필이 없으면 생성, 있으면 가져옴)
        profile, created = UserProfile.objects.get_or_create(user=instance)
        
        if cooking_level is not None:
            profile.cooking_level = cooking_level
        if allergies is not None:
            profile.allergies = allergies
        if banned_ingredients is not None:
            profile.banned_ingredients = banned_ingredients
        
        profile.save()
        return instance