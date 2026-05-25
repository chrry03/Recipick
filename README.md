<div align="center">

# 🥕 레시픽 (Recipick)

### *"집에 있는 식재료로, 지금 나에게 딱 맞는 레시피"*

**냉장고 속 재료와 유통기한을 기준으로, 지금 당장 해먹을 수 있는 현실적인 레시피를 추천해주는 서비스**

<br>

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?style=flat-square&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.15-A30000?style=flat-square&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-EB%20%2B%20S3%20%2B%20RDS-FF9900?style=flat-square&logo=amazonaws&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

</div>

<br>

## 📖 목차

- [🍳 레시픽을 왜 만들었나요?](#-레시픽을-왜-만들었나요)
- [✨ 핵심 가치](#-핵심-가치)
- [🎯 주요 기능](#-주요-기능)
- [🧠 추천 알고리즘](#-추천-알고리즘)
- [🛠️ 기술 스택](#️-기술-스택)
- [🏗️ 프로젝트 구조](#️-프로젝트-구조)
- [🚀 시작하기](#-시작하기)
- [📡 API 문서](#-api-문서)
- [👥 팀원](#-팀원)

<br>

## 🍳 레시픽을 왜 만들었나요?

> *"오늘 뭐 해먹지?"* — 매일 반복되는 이 고민, 한 번쯤 해보셨을 거예요.

많은 사람들이 요리를 못하는 이유는 **"레시피가 없어서"가 아니라 "지금 내 상황에 맞는 레시피가 없어서"** 입니다.

- 🥬 냉장고에 뭐가 있는지 모르겠고
- ⏰ 유통기한 지나서 버리는 재료가 아깝고
- 🍽️ 자취·통학으로 매일 끼니 챙기기는 막막하고
- 📱 레시피 앱은 너무 많은데, 정작 "지금 내가 만들 수 있는 것"은 알려주지 않죠

**레시픽은 이 문제에서 출발했습니다.**
지금 내 냉장고 기준, 내 식습관 기준, 내 요리 실력 기준으로 — **"지금 가능한 선택지"** 를 제안하는 서비스예요.

<br>

## ✨ 핵심 가치

| 가치 | 설명 |
|:---:|:---|
| 🥗 **현실적인 추천** | 지금 내 냉장고에 있는 재료로 실제로 만들 수 있는 레시피만 보여줍니다 |
| 🛡️ **안전한 추천** | 알러지, 비건, 기피 식재료를 원천 차단해서 추천합니다 |
| ♻️ **낭비 최소화** | 유통기한 임박 식재료를 사용하는 레시피를 우선 추천해 음식물 쓰레기를 줄입니다 |
| 📈 **지속적 개인화** | 요리 일지를 쌓을수록 내 취향에 맞는 추천이 점점 정확해집니다 |

<br>

## 🎯 주요 기능

### 🔐 1. 회원/사용자 설정
- **일반 로그인** + **소셜 로그인** (Google · Kakao · Naver) — JWT 기반 인증
- **취향 설정**: 알러지, 기피 식재료, 요리 숙련도 (초보/중급/숙련)
- 비회원도 레시피 **검색 및 상세 조회** 가능 (찜·일지 등은 로그인 필요)

### 🥦 2. 식재료 등록 및 관리
- **카테고리 기반 선택형 등록** (채소 / 육류 / 해산물 / 유제품 / 가공식품 / 기타 …)
- 리스트에 없는 식재료는 **직접 추가** 가능
- **유통기한은 선택 입력** — 입력하지 않아도 추천은 정상 작동
- 한국어/영어 식재료 자동 매핑 (Spoonacular API 연동을 위한 다국어 처리)

### 🔍 3. 레시피 검색 & 추천
- **키워드 검색** — 메뉴명 / 재료명으로 자유롭게 검색
- **맞춤 추천** — 보유 식재료 + 유통기한 + 알러지 + 숙련도 종합 반영
- **두 데이터 소스 통합 활용**
  - 🇰🇷 식품의약품안전처 공공데이터 (**한식 레시피 1,146개**)
  - 🌍 [Spoonacular API](https://spoonacular.com/food-api) (해외 레시피)
- 영문 레시피는 **자동 한글 번역** 후 노출

### 🍳 4. 레시피 상세 & 요리 모드
- 단계별 조리법 표시
- 단계 중간 **타이머** 기능 (프론트엔드)
- 한글 제목 우선 표시 (해외 레시피도 번역본 노출)

### 📓 5. 요리 일지
- 조리 완료 → 일지 작성으로 자연스럽게 연결
- **별점 · 체감 난이도 · 메모 · 사진** 기록
- 월별 캘린더 조회 / 상세 조회
- **인스타 스토리 공유** (9:16 비율 이미지 자동 생성)
- 이번 요리로 소진한 식재료 자동 차감

### 🔔 6. 유통기한 알림
- 임박 식재료 푸시 알림
- 헤더 종모양 아이콘 알림 탭에서 모아보기
- 임박 재료 활용 레시피를 홈 추천에 **상단 우선 노출**

<br>

## 🧠 추천 알고리즘

레시픽의 핵심은 **4가지 요소를 가중치로 종합하는 추천 점수 시스템**입니다.

```
총점 = (재료 매칭 45%) + (유통기한 임박도 40%) + (난이도 적합도 10%) + (개인화 5%)
```

| 점수 요소 | 가중치 | 설명 |
|:---|:---:|:---|
| 🥕 **재료 매칭** | **45%** | 보유 재료와 레시피 재료의 일치율. 부족한 재료가 적을수록 높은 점수 |
| ⏰ **유통기한 임박도** | **40%** | 임박 식재료를 사용하는 레시피일수록 가산점 (낭비 방지 핵심 가중치) |
| 🎚️ **난이도 적합도** | **10%** | 사용자 숙련도와 레시피 난이도의 거리 |
| 👤 **개인화** | **5%** | 요리 일지 누적 기반 선호 패턴 반영 |

### 📂 추천 결과 분류

추천 결과는 사용자가 한눈에 우선순위를 파악할 수 있도록 **3개 그룹**으로 분류됩니다.

| 카테고리 | 라벨 | 조건 |
|:---:|:---|:---|
| 🚨 | **소비기한 임박 레시피** | 임박/만료 재료를 활용하는 레시피 |
| ✅ | **지금 바로 만들 수 있어요** | 부족한 재료 0개 |
| 🛒 | **재료 1-2개만 있으면 가능해요** | 1~2개 추가 재료만 필요 |

**필터링 우선순위**: ① 알러지/기피 식재료 제외 → ② 점수 계산 → ③ 카테고리 분류 → ④ 정렬

<br>

## 🛠️ 기술 스택

### Backend
| 영역 | 기술 |
|:---|:---|
| **Language** | Python 3.11 |
| **Framework** | Django 5.2 · Django REST Framework 3.15 |
| **Auth** | SimpleJWT (Access/Refresh 토큰) + Django Allauth |
| **Database** | PostgreSQL (운영) · SQLite (개발) |
| **Cache** | File-based Cache (Redis 전환 준비 완료) |
| **Storage** | AWS S3 (django-storages + boto3) |
| **Static** | WhiteNoise (압축·캐시 헤더 자동 처리) |
| **API Docs** | drf-yasg (Swagger / ReDoc) |

### Frontend
- HTML5 · CSS3 · Vanilla JavaScript
- Django Templates 기반 SSR + AJAX

### External APIs & Data
- 🌍 **Spoonacular API** — 해외 레시피 데이터
- 🇰🇷 **식품의약품안전처 공공데이터** — 한식 레시피 1,146개
- 🌐 **deep-translator / googletrans** — 영↔한 자동 번역

### Infrastructure
- **Docker** + docker-compose
- **AWS Elastic Beanstalk** (배포)
- **AWS RDS** (PostgreSQL)
- **AWS S3** (미디어 파일)
- **Gunicorn** (WSGI 서버)

<br>

## 🏗️ 프로젝트 구조

```
Recipick/
├── config/                  # Django 프로젝트 설정
│   ├── settings.py          # 환경별 분기 (SQLite ↔ RDS, S3, JWT, CORS 등)
│   └── urls.py              # 메인 라우팅 + Swagger
│
├── users/                   # 👤 회원 · 인증 · 프로필
│   ├── models.py            # User, UserProfile, SocialAccount
│   └── views.py             # 일반/소셜 로그인, 마이페이지
│
├── ingredients/             # 🥦 식재료 마스터 / 사용자 보유 / 카테고리
│   ├── models.py            # IngredientCategory, IngredientMaster,
│   │                        # IngredientNameMapping, UserIngredient
│   ├── utils/               # 한↔영 식재료 매퍼
│   └── views.py
│
├── recipes/                 # 🍳 레시피 · 추천 · 검색
│   ├── models.py            # Recipe, RecipeIngredient, FavoriteRecipe
│   ├── utils.py             # 추천 알고리즘 핵심 로직
│   ├── services/
│   │   ├── spoonacular.py   # Spoonacular API 클라이언트
│   │   └── translator.py    # 영문 레시피 자동 번역
│   └── management/commands/
│       ├── setup_recipick.py            # 통합 초기 셋업
│       ├── load_korean_recipes.py       # 한식 1,146개 적재
│       └── fetch_and_translate_recipes.py
│
├── logs/                    # 📓 요리 일지
│   └── models.py            # RecipeLog (별점, 난이도, 메모, 사진, 공유 이미지)
│
├── templates/               # Django 템플릿
├── static/                  # CSS · JS · 이미지 · 폰트 · 사운드
├── fixtures/                # 초기 데이터 (카테고리, 식재료)
│   ├── categories.json
│   └── ingredients.json
├── foodsafetykorea.json     # 식약처 한식 원본 데이터
├── hardcoded_recipes.json   # 큐레이션 한식 레시피
│
├── Dockerfile
├── docker-compose.dev.yml
└── requirements.txt
```

<br>

## 🚀 시작하기

### 사전 준비물

- Python **3.11+**
- PostgreSQL **14+** *(또는 SQLite로 빠른 시작 가능)*
- Docker *(선택)*
- Spoonacular API Key — [발급 받기](https://spoonacular.com/food-api)

### 1️⃣ 저장소 클론

```bash
git clone https://github.com/your-org/Recipick.git
cd Recipick
```

### 2️⃣ 환경변수 설정

루트 디렉토리에 `.env` 파일을 만들고 아래 값을 채워주세요.

```dotenv
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Database (선택 — 미설정 시 SQLite 자동 사용)
DB_NAME=recipick
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Spoonacular API
SPOONACULAR_API_KEY=your-spoonacular-key

# AWS S3 (운영 환경)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret

# Social OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=...

KAKAO_CLIENT_ID=...
KAKAO_CLIENT_SECRET=...
KAKAO_REDIRECT_URI=...

NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
NAVER_REDIRECT_URI=...

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 3️⃣ 로컬 실행

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# DB 마이그레이션
python manage.py migrate

# 🍱 초기 데이터 세팅 (카테고리 + 식재료 + 한식 레시피 1,146개)
python manage.py setup_recipick

# 관리자 계정 생성 (선택)
python manage.py createsuperuser

# 개발 서버 실행 🎉
python manage.py runserver
```

브라우저에서 [http://127.0.0.1:8000](http://127.0.0.1:8000) 으로 접속하세요!

### 4️⃣ Docker로 실행

```bash
docker-compose -f docker-compose.dev.yml up --build
```

### 5️⃣ 초기 데이터 옵션

`setup_recipick` 명령어는 다양한 옵션을 지원합니다.

```bash
# 전체 셋업 (기본)
python manage.py setup_recipick

# 일부 단계만 건너뛰기
python manage.py setup_recipick --skip-fixtures      # fixtures 건너뛰기
python manage.py setup_recipick --skip-mappings      # 식재료 매핑 건너뛰기
python manage.py setup_recipick --skip-recipes       # 한식 레시피 로드 건너뛰기

# Spoonacular API 연결 테스트
python manage.py setup_recipick --test-spoonacular

# 테스트 사용자 + 샘플 식재료 생성
python manage.py setup_recipick --create-test-user
```

<br>

## 📡 API 문서

서버 실행 후 아래 URL에서 자동 생성된 API 문서를 확인할 수 있습니다.

- **Swagger UI**: [http://127.0.0.1:8000/swagger/](http://127.0.0.1:8000/swagger/)
- **ReDoc**: [http://127.0.0.1:8000/redoc/](http://127.0.0.1:8000/redoc/)

### 주요 엔드포인트 한눈에 보기

<details>
<summary><b>👤 회원 / 인증</b></summary>

| Method | Endpoint | 설명 | Auth |
|:---:|:---|:---|:---:|
| POST | `/api/users/signup/` | 회원가입 | ❌ |
| POST | `/api/users/login/` | 로그인 | ❌ |
| POST | `/api/users/social/login/{provider}/` | 소셜 로그인 | ❌ |
| POST | `/api/users/token/refresh/` | 토큰 재발급 | ❌ |
| POST | `/api/users/logout/` | 로그아웃 | ✅ |
| GET | `/api/users/me/` | 내 정보 조회 | ✅ |
| PATCH | `/api/users/me/` | 내 정보 수정 (취향 포함) | ✅ |
| DELETE | `/api/users/me/` | 회원 탈퇴 | ✅ |
| GET | `/api/users/check-nickname/` | 닉네임 중복 확인 | ❌ |

</details>

<details>
<summary><b>🥦 식재료</b></summary>

| Method | Endpoint | 설명 | Auth |
|:---:|:---|:---|:---:|
| GET | `/ingredients` | 식재료 마스터 목록 | ❌ |
| GET | `/ingredients/categories` | 카테고리 목록 | ❌ |
| GET | `/ingredients/search?keyword=` | 자동완성 검색 | ❌ |
| POST | `/user-ingredients` | 내 식재료 등록 | ✅ |
| GET | `/user-ingredients` | 내 식재료 조회 | ✅ |
| GET | `/user-ingredients/expiring` | 유통기한 임박 식재료 | ✅ |
| PATCH | `/user-ingredients/{id}` | 식재료 수정 (유통기한 등) | ✅ |
| PATCH | `/user-ingredients/{id}/consume` | 소비 처리 | ✅ |
| DELETE | `/user-ingredients/{id}` | 삭제 | ✅ |

</details>

<details>
<summary><b>🍳 레시피</b></summary>

| Method | Endpoint | 설명 | Auth |
|:---:|:---|:---|:---:|
| GET | `/recipes?sort=recommend` | 추천순 레시피 목록 | ❌ |
| GET | `/recipes/{id}` | 레시피 상세 | ❌ |
| GET | `/recipes/search?keyword=` | 레시피 검색 | ❌ |
| POST | `/recipes/{id}/favorite` | 찜하기 / 취소 | ✅ |
| GET | `/recipes/favorites` | 찜한 레시피 목록 | ✅ |

</details>

<details>
<summary><b>📓 요리 일지</b></summary>

| Method | Endpoint | 설명 | Auth |
|:---:|:---|:---|:---:|
| POST | `/api/logs/` | 일지 작성 | ✅ |
| GET | `/api/logs/` | 월별 일지 조회 | ✅ |
| GET | `/api/logs/{id}/` | 일지 상세 | ✅ |
| PATCH | `/api/logs/{id}/` | 일지 수정 | ✅ |
| DELETE | `/api/logs/{id}/` | 일지 삭제 | ✅ |

</details>

<br>

## 📦 MVP 범위

### ✅ MVP에 포함된 기능
- 사용자 정보 설정 (알러지 / 기피 재료 / 숙련도)
- 식재료 카테고리 기반 등록 + 직접 추가
- 보유 식재료 + 유통기한 기반 추천
- 키워드 레시피 검색
- 한식 + 해외 레시피 통합
- 요리 일지 작성 / 조회 / 인스타 공유
- 유통기한 임박 알림

### ⏳ 향후 확장 예정
- 📸 사진 인식 기반 식재료 자동 등록
- 🎥 레시피 설명 영상 / 영상 일지
- 🍴 보유 조리 도구 기반 필터링 고도화
- 🤝 요리 일지 커뮤니티 / 팔로우 기능

<br>

## 👥 팀원

이 프로젝트는 **5명의 팀원이 협업**하여 개발했습니다.

<br>

## 📄 라이선스

이 프로젝트는 학습 및 포트폴리오 목적으로 제작되었으며, MIT 라이선스를 따릅니다.

레시피 데이터 출처:
- 🇰🇷 [식품의약품안전처 공공데이터 포털](https://www.foodsafetykorea.go.kr/)
- 🌍 [Spoonacular Food API](https://spoonacular.com/food-api)

<br>

---

<div align="center">

### 🥕 *오늘 뭐 해먹지? 레시픽이 알려드릴게요.*

</div>