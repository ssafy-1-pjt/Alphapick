from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    profile_image_url = serializers.SerializerMethodField()
    remove_profile_image = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "nickname",
            "profile_image",
            "profile_image_url",
            "remove_profile_image",
            "risk_type",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def get_profile_image_url(self, obj):
        if not obj.profile_image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.profile_image.url) if request else obj.profile_image.url

    def validate_nickname(self, value):
        nickname = value.strip()
        if nickname and len(nickname) < 2:
            raise serializers.ValidationError("닉네임은 2자 이상 입력해 주세요.")
        queryset = User.objects.filter(nickname__iexact=nickname)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if nickname and queryset.exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return nickname

    def update(self, instance, validated_data):
        remove_profile_image = validated_data.pop("remove_profile_image", False)
        if remove_profile_image and instance.profile_image:
            instance.profile_image.delete(save=False)
            instance.profile_image = None
        return super().update(instance, validated_data)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=True)

    allowed_email_domains = {
        "gmail.com",
        "google.com",
        "naver.com",
        "daum.net",
        "hanmail.net",
        "kakao.com",
        "outlook.com",
        "hotmail.com",
        "icloud.com",
        "yahoo.com",
    }

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "password",
            "nickname",
            "risk_type",
        )

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def validate_email(self, value):
        email = value.strip().lower()
        domain = email.rsplit("@", 1)[-1]
        if domain not in self.allowed_email_domains:
            raise serializers.ValidationError("지원하는 메일 서비스 주소를 입력해 주세요. 예: name@gmail.com, name@naver.com")
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("이미 가입된 이메일 주소입니다.")
        return email

    def validate_username(self, value):
        username = value.strip()
        if len(username) < 3:
            raise serializers.ValidationError("아이디는 영문, 숫자, 밑줄을 사용해 3자 이상 입력해 주세요.")
        if not username.replace("_", "").isalnum() or not username.isascii():
            raise serializers.ValidationError("아이디는 영문, 숫자, 밑줄(_)만 사용할 수 있습니다.")
        return username

    def validate_nickname(self, value):
        nickname = value.strip()
        if nickname and len(nickname) < 2:
            raise serializers.ValidationError("닉네임은 2자 이상 입력해 주세요.")
        if nickname and User.objects.filter(nickname__iexact=nickname).exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return nickname

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class AlphaPickTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
