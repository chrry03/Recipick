/**
 * 레시피 관련 JavaScript 모듈
 * 레시피 목록, 상세, 단계별 요리 모드 등의 기능을 통합 관리
 */

(function() {
    'use strict';

    // ============================================
    // 공통 유틸리티 함수
    // ============================================

    /**
     * Cookie 값 가져오기
     * @param {String} name - Cookie 이름
     * @returns {String|null} Cookie 값
     */
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return null;
    }

    /**
     * CSRF Token 가져오기
     * @returns {String|null} CSRF Token
     */
    function getCsrfToken() {
        const dataElement = document.querySelector('[data-csrf-token]');
        if (dataElement) {
            return dataElement.dataset.csrfToken || '';
        }
        return getCookie('csrftoken');
    }

    /**
     * Access Token 가져오기 (localStorage 또는 cookie)
     * @returns {String|null} Access Token
     */
    function getAccessToken() {
        const token = localStorage.getItem('access_token');
        if (token) {
            return token;
        }
        const cookieToken = getCookie('access_token');
        return cookieToken;
    }

    /**
     * Access Token 갱신
     * @returns {Promise<Boolean>} 갱신 성공 여부
     */
    async function refreshAccessToken() {
        const refreshToken = localStorage.getItem('refresh_token') || getCookie('refresh_token');
        
        if (!refreshToken) {
            console.error('Refresh token이 없습니다');
            return false;
        }
        
        try {
            const response = await fetch('/api/users/token/refresh/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    refresh: refreshToken
                })
            });
            
            if (!response.ok) {
                throw new Error('토큰 갱신 실패');
            }
            
            const data = await response.json();
            localStorage.setItem('access_token', data.access);
            console.log('Access token 갱신 성공');
            return true;
            
        } catch (error) {
            console.error('토큰 갱신 오류:', error);
            alert('로그인이 만료되었습니다. 다시 로그인해주세요.');
            window.location.href = '/users/login/';
            return false;
        }
    }

    /**
     * HTML 이스케이프
     * @param {String} text - 이스케이프할 텍스트
     * @returns {String} 이스케이프된 HTML
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ============================================
    // 레시피 추천 API 모듈
    // ============================================

    /**
     * 레시피 추천 API 호출
     * @param {Array} ingredientIds - 선택한 식재료 ID 배열
     * @param {Boolean} useAll - 모든 식재료 사용 여부
     * @param {Boolean} includeSpoonacular - Spoonacular API 사용 여부
     * @param {Number} maxResults - 최대 결과 개수
     * @returns {Promise} API 응답 데이터
     */
    async function getRecipeRecommendations(ingredientIds = [], useAll = true, includeSpoonacular = true, maxResults = 20) {
        const token = getAccessToken();
        
        if (!token) {
            console.error('로그인이 필요합니다');
            throw new Error('로그인이 필요합니다');
        }
        
        try {
            const response = await fetch('/api/recipes/api/recommendations/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    ingredient_ids: ingredientIds,
                    use_all: useAll,
                    include_spoonacular: includeSpoonacular,
                    max_results: maxResults
                })
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    const refreshed = await refreshAccessToken();
                    if (refreshed) {
                        return getRecipeRecommendations(ingredientIds, useAll, includeSpoonacular, maxResults);
                    } else {
                        throw new Error('로그인이 만료되었습니다. 다시 로그인해주세요.');
                    }
                }
                throw new Error(`API 호출 실패: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('레시피 추천 성공:', data);
            return data;
            
        } catch (error) {
            console.error('레시피 추천 API 오류:', error);
            throw error;
        }
    }

    /**
     * 레시피 검색 API 호출
     * @param {String} query - 검색 키워드
     * @returns {Promise} API 응답 데이터
     */
    async function searchRecipes(query) {
        try {
            const response = await fetch(`/api/recipes/api/search/?q=${encodeURIComponent(query)}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`검색 실패: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('레시피 검색 성공:', data);
            return data;
            
        } catch (error) {
            console.error('레시피 검색 API 오류:', error);
            throw error;
        }
    }

    /**
     * 레시피 카드 HTML 생성
     * @param {Object} recipe - 레시피 데이터
     * @returns {String} HTML 문자열
     */
    function createRecipeCard(recipe) {
        const difficultyMap = {
            'EASY': '쉬움',
            'NORMAL': '보통',
            'DIFFICULT': '어려움'
        };
        const difficultyText = difficultyMap[recipe.difficulty] || '보통';
        
        const score = recipe.recommendation_score || {};
        const totalScore = score.total_score || 0;
        const missingCount = score.missing_ingredients_count || 0;
        
        const imageUrl = recipe.image_url || '/static/images/default-recipe.jpg';
        
        let scoreClass = '';
        if (totalScore >= 90) {
            scoreClass = 'score-urgent';
        } else if (totalScore >= 75) {
            scoreClass = 'score-ready';
        } else {
            scoreClass = 'score-almost';
        }
        
        return `
            <div class="recipe-card" data-recipe-id="${recipe.recipe_id}">
                <img src="${imageUrl}" 
                     alt="${escapeHtml(recipe.title)}" 
                     class="recipe-image"
                     data-default-image="/static/images/default-recipe.jpg"
                     loading="lazy">
                <div class="recipe-info">
                    <div class="recipe-name">${escapeHtml(recipe.title)}</div>
                    <div class="recipe-meta">
                        <span class="recipe-time">⏱️ ${recipe.ready_minutes}분</span>
                        <span class="recipe-difficulty">${difficultyText}</span>
                    </div>
                    ${totalScore > 0 ? `
                        <div class="score-badge ${scoreClass}">
                            추천 ${totalScore.toFixed(0)}점
                            ${missingCount > 0 ? ` (재료 ${missingCount}개 부족)` : ''}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * 카테고리 섹션 렌더링
     * @param {String} title - 섹션 제목
     * @param {Array} recipes - 레시피 배열
     * @param {String} categoryClass - CSS 클래스
     * @returns {String} HTML 문자열
     */
    function renderCategorySection(title, recipes, categoryClass) {
        let html = `
            <div class="recommendation-section ${categoryClass}">
                <h2 class="section-title">${title}</h2>
                <div class="recipe-grid">
        `;
        
        recipes.forEach(recipe => {
            html += createRecipeCard(recipe);
        });
        
        html += `
                </div>
            </div>
        `;
        
        return html;
    }

    /**
     * 레시피 추천 결과 렌더링
     * @param {Object} data - API 응답 데이터
     */
    function renderRecipeRecommendations(data) {
        const container = document.getElementById('recipe-recommendations');
        
        if (!container) {
            console.error('recipe-recommendations 컨테이너를 찾을 수 없습니다');
            return;
        }
        
        if (data.total_count === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>추천할 레시피가 없습니다.<br>
                    다른 식재료를 등록해보세요!</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        const categories = data.categories;
        
        if (categories.urgent_ready && categories.urgent_ready.count > 0) {
            html += renderCategorySection(
                '🔥 ' + categories.urgent_ready.label,
                categories.urgent_ready.recipes,
                'urgent'
            );
        }
        
        if (categories.ready && categories.ready.count > 0) {
            html += renderCategorySection(
                '✨ ' + categories.ready.label,
                categories.ready.recipes,
                'ready'
            );
        }
        
        if (categories.almost_ready && categories.almost_ready.count > 0) {
            html += renderCategorySection(
                '👍 ' + categories.almost_ready.label,
                categories.almost_ready.recipes,
                'almost'
            );
        }
        
        container.innerHTML = html;
        attachRecipeCardListeners();
    }

    /**
     * 레시피 카드 이벤트 리스너 추가
     */
    function attachRecipeCardListeners() {
        const cards = document.querySelectorAll('.recipe-card[data-recipe-id]');
        cards.forEach(card => {
            card.addEventListener('click', function() {
                const recipeId = this.dataset.recipeId;
                if (recipeId) {
                    window.location.href = `/recipes/${recipeId}/`;
                }
            });
        });
        
        const images = document.querySelectorAll('.recipe-image[data-default-image]');
        images.forEach(img => {
            img.addEventListener('error', function() {
                this.src = this.dataset.defaultImage;
            });
        });
    }

    /**
     * 이미지 에러 핸들러 추가
     */
    function attachImageErrorHandlers() {
        const images = document.querySelectorAll('.recipe-image[data-default-image], .step-image[data-fallback-display]');
        images.forEach(img => {
            img.addEventListener('error', function() {
                if (this.dataset.defaultImage) {
                    this.src = this.dataset.defaultImage;
                } else if (this.dataset.fallbackDisplay) {
                    this.style.display = this.dataset.fallbackDisplay || 'none';
                }
            });
        });
    }

    // ============================================
    // 레시피 목록 페이지 모듈
    // ============================================
// ============================================
    // [수정] 레시피 카드 생성 함수 (Figma 디자인 반영)
    // ============================================
    function createRecipeCard(recipe) {
        const difficultyMap = { 'EASY': '쉬움', 'NORMAL': '보통', 'DIFFICULT': '어려움' };
        const difficultyText = difficultyMap[recipe.difficulty] || '보통';
        
        // 추천 점수 데이터가 있으면 활용
        const scoreData = recipe.recommendation_score || {};
        const missingCount = scoreData.missing_ingredients_count || 0;
        
        // 재료 상태 텍스트 생성
        let ownedText = "정보 없음";
        let missingText = "-";

        // API 응답 구조에 따라 재료 텍스트 처리
        if (recipe.ingredients_status) {
            // 상세 상태가 있는 경우
            const status = recipe.ingredients_status;
            const owned = Object.keys(status).filter(k => status[k] !== 'missing');
            const missing = Object.keys(status).filter(k => status[k] === 'missing');
            
            ownedText = owned.length > 0 ? owned.join(', ') : '없음';
            missingText = missing.length > 0 ? missing.join(', ') : '없음';
        } else {
            // 기본 정보만 있는 경우
            ownedText = "보유 재료 포함";
            missingText = missingCount > 0 ? `${missingCount}개 부족` : '없음';
        }

        const imageUrl = recipe.image_url || '/static/images/default-recipe.jpg';
        const isFavorited = recipe.is_favorited; 

        return `
            <div class="recipe-card" onclick="location.href='/recipes/${recipe.recipe_id}/'">
                <button class="favorite-btn ${isFavorited ? '' : 'inactive'}" 
                        onclick="event.stopPropagation(); toggleLike(${recipe.recipe_id}, this)">
                    ★
                </button>
                
                <h3 class="recipe-title">${escapeHtml(recipe.title)}</h3>
                
                <div class="recipe-image-wrapper">
                    <img src="${imageUrl}" alt="${escapeHtml(recipe.title)}" class="recipe-image" 
                         onerror="this.src='/static/images/default-recipe.jpg'">
                </div>
                
                <div class="info-rows">
                    <div class="info-row">
                        <span class="info-label">예상 조리시간</span>
                        <span class="info-value">${recipe.ready_minutes}분</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">난이도</span>
                        <span class="info-value">${difficultyText}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">보유 재료</span>
                        <span class="info-value">${ownedText}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">없는 재료</span>
                        <span class="info-value" style="color: #999;">${missingText}</span>
                    </div>
                </div>
            </div>
        `;
    }

    // ============================================
    // [수정] 레시피 목록 페이지 초기화 (전면 수정)
    // ============================================
    function initRecipeList() {
        const searchInput = document.getElementById('recipe-search-input');
        const spinner = document.getElementById('loading-spinner');
        const resultsContainer = document.getElementById('recipe-recommendations');
        const filterChips = document.querySelectorAll('.filter-chip');
        
        // 컨테이너가 없으면 실행 중지 (다른 페이지임)
        if (!resultsContainer) return;

        // 현재 활성화된 필터 ('all', 'favorites', 'my-ingredients')
        let currentFilter = 'all'; 

        /**
         * 레시피 데이터 로드 및 렌더링
         * @param {String} type - 'recommend' | 'search'
         * @param {String} query - 검색어 (type이 search일 때)
         */
        async function loadRecipes(type, query = '') {
            spinner.classList.add('show');
            resultsContainer.innerHTML = '';

            try {
                let data;
                
                if (type === 'search') {
                    // 검색 API 호출
                    data = await searchRecipes(query);
                } else {
                    // 필터에 따른 API 호출 분기
                    if (currentFilter === 'favorites') {
                        // [TODO] 찜한 레시피 API 호출 (현재는 임시 처리)
                        // data = await getFavoriteRecipes(); 
                        alert("찜한 레시피 기능은 준비 중입니다.");
                        spinner.classList.remove('show');
                        updateFilterCounts(0);
                        return;
                    } else {
                        // 'all' 또는 'my-ingredients'는 추천 API 사용
                        // (ingredient_ids가 비어있으면 전체 보유 재료 기반 추천)
                        data = await getRecipeRecommendations([], true, true);
                    }
                }
                
                // 데이터 구조 표준화 (검색 결과 vs 추천 결과)
                let recipes = [];
                if (data.recipes) {
                    recipes = data.recipes;
                } else if (data.categories) {
                    // 추천 API는 카테고리별로 오므로 합쳐서 보여줌
                    // (Figma 디자인은 통짜 리스트이므로 병합)
                    recipes = [
                        ...data.categories.urgent_ready.recipes,
                        ...data.categories.ready.recipes,
                        ...data.categories.almost_ready.recipes
                    ];
                }

                // 결과 렌더링
                if (recipes.length === 0) {
                    resultsContainer.innerHTML = `
                        <div class="empty-state">
                            <img src="/static/images/empty_fridge.png" alt="결과 없음" style="width: 80px; opacity: 0.5;">
                            <p>${type === 'search' ? '검색 결과가 없습니다.' : '추천할 레시피가 없습니다.'}</p>
                        </div>`;
                } else {
                    let html = '';
                    recipes.forEach(recipe => {
                        html += createRecipeCard(recipe);
                    });
                    resultsContainer.innerHTML = html;
                }
                
                // 필터 칩의 숫자(Count) 업데이트
                updateFilterCounts(recipes.length);

            } catch (error) {
                console.error('레시피 로드 실패:', error);
                resultsContainer.innerHTML = `
                    <div class="empty-state">
                        <p>레시피를 불러오지 못했습니다.<br>잠시 후 다시 시도해주세요.</p>
                    </div>`;
            } finally {
                spinner.classList.remove('show');
            }
        }

        /**
         * 필터 칩의 카운트 숫자 업데이트
         */
        function updateFilterCounts(count) {
            const activeChip = document.querySelector(`.filter-chip[data-filter="${currentFilter}"]`);
            if (activeChip) {
                const countSpan = activeChip.querySelector('.count');
                if (countSpan) countSpan.textContent = `(${count})`;
            }
        }

        // 1. 초기 로드: 페이지 열리면 바로 추천 레시피 가져오기
        loadRecipes('recommend');

        // 2. 검색 이벤트 (Enter 키)
        if (searchInput) {
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    const query = this.value.trim();
                    if (query) {
                        // 검색 시 필터 해제 UI 처리 (선택사항)
                        loadRecipes('search', query);
                    } else {
                        loadRecipes('recommend'); // 검색어 없으면 다시 추천 목록
                    }
                }
            });
        }

        // 3. 필터 칩 클릭 이벤트
        filterChips.forEach(chip => {
            chip.addEventListener('click', function() {
                // UI 활성화 변경
                filterChips.forEach(c => c.classList.remove('active'));
                this.classList.add('active');
                
                // 필터 상태 변경 및 데이터 로드
                currentFilter = this.dataset.filter;
                loadRecipes('recommend');
            });
        });
        
        // 이미지 로딩 에러 핸들러 연결
        attachImageErrorHandlers();
    }

    // ============================================
    // 레시피 상세 페이지 모듈
    // ============================================

    /**
     * 레시피 상세 페이지 초기화    
     */
    function initRecipeDetail() {
        const backBtn = document.getElementById('backBtn');
        const likeBtn = document.getElementById('likeBtn');
        const dataElement = document.querySelector('[data-favorite-url]');
        
        /**
         * 좋아요 토글 처리
         */
        async function toggleFavorite() {
            if (!likeBtn || !dataElement) {
                return;
            }
            
            const recipeId = likeBtn.dataset.recipeId;
            if (!recipeId) {
                console.error('레시피 ID를 찾을 수 없습니다.');
                return;
            }
            
            const favoriteUrl = dataElement.dataset.favoriteUrl;
            if (!favoriteUrl) {
                console.error('좋아요 URL을 찾을 수 없습니다.');
                return;
            }
            
            const originalText = likeBtn.textContent;
            likeBtn.disabled = true;
            
            try {
                const response = await fetch(favoriteUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                
                if (data.is_favorite) {
                    likeBtn.textContent = '❤️';
                    likeBtn.setAttribute('aria-pressed', 'true');
                } else {
                    likeBtn.textContent = '🤍';
                    likeBtn.setAttribute('aria-pressed', 'false');
                }
            } catch (error) {
                console.error('좋아요 처리 실패:', error);
                likeBtn.textContent = originalText;
                alert('좋아요 처리 중 오류가 발생했습니다.');
            } finally {
                likeBtn.disabled = false;
            }
        }

        /**
         * 뒤로가기 처리
         */
        function handleBackClick() {
            if (window.history.length > 1) {
                history.back();
            } else {
                window.location.href = '/recipes/';
            }
        }

        // 이벤트 리스너 등록
        if (backBtn) {
            backBtn.addEventListener('click', handleBackClick);
        }
        
        if (likeBtn) {
            likeBtn.addEventListener('click', toggleFavorite);
        }
    }

    // ============================================
    // 레시피 단계
    // ============================================

    class RecipeStepNavigator {
        constructor(options = {}) {
            this.currentStep = this._getCurrentStep();
            this.totalSteps = options.totalSteps || this._getTotalSteps();
            this.recipeId = options.recipeId || this._getRecipeId();
            this.baseUrl = options.baseUrl || '/recipes';
            this.swipeThreshold = options.swipeThreshold || 50;
            
            this.touchStartX = 0;
            this.touchEndX = 0;
            
            this._init();
        }

        _getCurrentStep() {
            const stepElement = document.querySelector('.step-number p');
            if (stepElement) {
                const stepText = stepElement.textContent.trim();
                const stepNumber = parseInt(stepText, 10);
                return isNaN(stepNumber) ? 1 : stepNumber;
            }
            return 1;
        }

        _getTotalSteps() {
            const container = document.querySelector('.recipe-container');
            if (container && container.dataset.totalSteps) {
                return parseInt(container.dataset.totalSteps, 10);
            }
            return 5;
        }

        _getRecipeId() {
            const container = document.querySelector('.recipe-container');
            if (container && container.dataset.recipeId) {
                return container.dataset.recipeId;
            }
            const match = window.location.pathname.match(/\/recipes\/(\d+)\//);
            return match ? match[1] : null;
        }

        _init() {
            this._bindEvents();
            this._updateButtonStates();
        }

        _bindEvents() {
            const prevBtn = document.querySelector('.btn-prev');
            const nextBtn = document.querySelector('.btn-next');
            const exitBtn = document.querySelector('.btn-exit');
            
            if (prevBtn) {
                prevBtn.addEventListener('click', () => this.goToPrevStep());
            }
            
            if (nextBtn) {
                nextBtn.addEventListener('click', () => this.goToNextStep());
            }
            
            if (exitBtn) {
                exitBtn.addEventListener('click', () => this.exitCooking());
            }

            document.addEventListener('keydown', (e) => this._handleKeydown(e));
            document.addEventListener('touchstart', (e) => this._handleTouchStart(e));
            document.addEventListener('touchend', (e) => this._handleTouchEnd(e));
        }

        _handleKeydown(event) {
            if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                return;
            }

            if (event.key === 'ArrowLeft') {
                event.preventDefault();
                this.goToPrevStep();
            } else if (event.key === 'ArrowRight') {
                event.preventDefault();
                this.goToNextStep();
            }
        }

        _handleTouchStart(event) {
            this.touchStartX = event.changedTouches[0].screenX;
        }

        _handleTouchEnd(event) {
            this.touchEndX = event.changedTouches[0].screenX;
            this._handleSwipe();
        }

        _handleSwipe() {
            const diffX = this.touchStartX - this.touchEndX;
            
            if (Math.abs(diffX) < this.swipeThreshold) {
                return;
            }

            if (diffX > 0) {
                this.goToNextStep();
            } else {
                this.goToPrevStep();
            }
        }

        goToPrevStep() {
            if (this.currentStep <= 1) {
                console.log('첫 번째 단계입니다.');
                return;
            }

            const prevStep = this.currentStep - 1;
            this._navigateToStep(prevStep);
        }

        goToNextStep() {
            if (this.currentStep >= this.totalSteps) {
                // 마지막 단계에서 다음 버튼 클릭 시 완료 페이지로 이동
                this._navigateToComplete();
                return;
            }

            const nextStep = this.currentStep + 1;
            this._navigateToStep(nextStep);
        }

        _navigateToComplete() {
            if (!this.recipeId) {
                console.error('레시피 ID를 찾을 수 없습니다.');
                return;
            }

            try {
                const url = `${this.baseUrl}/${this.recipeId}/complete/`;
                window.location.href = url;
            } catch (error) {
                console.error('완료 페이지 이동 중 오류 발생:', error);
            }
        }

        _navigateToStep(step) {
            if (step < 1 || step > this.totalSteps) {
                console.error(`유효하지 않은 단계 번호: ${step}`);
                return;
            }

            try {
                const url = this._buildStepUrl(step);
                window.location.href = url;
            } catch (error) {
                console.error('단계 이동 중 오류 발생:', error);
            }
        }

        _buildStepUrl(step) {
            if (this.recipeId) {
                return `${this.baseUrl}/${this.recipeId}/step/${step}/`;
            }
            return `${this.baseUrl}/step/${step}/`;
        }

        exitCooking() {
            window.location.href = '/recipes/';
        }

        _updateButtonStates() {
            const nextBtn = document.querySelector('.btn-next');

            if (nextBtn) {
                // 마지막 단계에서도 다음 버튼을 활성화하여 완료 페이지로 이동 가능하도록 함
                nextBtn.disabled = false;
                nextBtn.classList.remove('disabled');
            }
        }
    }

    /**
     * 레시피 단계 네비게이션 초기화
     */
    function initRecipeStepNavigator() {
        const container = document.querySelector('.recipe-container');
        if (container) {
            window.recipeStepNavigator = new RecipeStepNavigator();
        }
    }

    // ============================================
    // 페이지 초기화
    // ============================================

    /**
     * 페이지 타입 감지 및 초기화
     */
    function init() {
        // 레시피 목록 페이지
        if (document.getElementById('recipe-recommendations')) {
            initRecipeList();
        }

        // 레시피 상세 페이지
        if (document.getElementById('likeBtn')) {
            initRecipeDetail();
        }

        // 요리 단계 페이지
        if (document.querySelector('.recipe-container[data-total-steps]')) {
            initRecipeStepNavigator();
            initTimer();
        }

        // 공통 이미지 에러 핸들러
        attachImageErrorHandlers();
    }

    // DOMContentLoaded 또는 즉시 실행
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // 전역으로 함수 노출 (다른 파일에서 사용 가능)
    window.getRecipeRecommendations = getRecipeRecommendations;
    window.searchRecipes = searchRecipes;
    window.renderRecipeRecommendations = renderRecipeRecommendations;
    window.attachRecipeCardListeners = attachRecipeCardListeners;

})();




    // ============================================
    // 타이머 모듈
    // ============================================

    const FULL_DASH_ARRAY = 283;
    const WARNING_THRESHOLD = 10;
    const ALERT_THRESHOLD = 5;

    const COLOR_CODES = {
        warning: {
            color: "orange"
        }
    };

    let TIME_LIMIT = 0;
    let timePassed = 0;
    let timeLeft = TIME_LIMIT;
    let timerInterval = null;
    let isEditingTime = false;
    let remainingPathColor = COLOR_CODES.warning.color;

    function formatTime(time) {
        const minutes = Math.floor(time / 60);
        let seconds = time % 60;

        if (seconds < 10) {
            seconds = `0${seconds}`;
        }

        return {
            minutes: minutes.toString(),
            seconds: seconds.toString(),
            display: `${minutes}:${seconds}`
        };
    }

    function parseTimeInput(input) {
        // "mm:ss" 또는 "m:ss" 형식 파싱
        const parts = input.split(':');
        if (parts.length === 2) {
            const minutes = parseInt(parts[0], 10) || 0;
            const seconds = parseInt(parts[1], 10) || 0;
            return minutes * 60 + seconds;
        }
        // 숫자만 입력된 경우 초로 간주
        const totalSeconds = parseInt(input, 10);
        return isNaN(totalSeconds) ? 0 : totalSeconds;
    }

    function updatePlayButtonState() {
        const playButton = document.getElementById("base-timer-play-button");
        if (playButton) {
            if (timerInterval) {
                // 타이머 실행 중 = 일시정지 버튼 표시
                playButton.classList.add("paused");
            } else {
                // 타이머 멈춤 = 재생 버튼 표시
                playButton.classList.remove("paused");
            }
        }
    }

    function onTimesUp() {
        clearInterval(timerInterval);
        timerInterval = null;
        updatePlayButtonState();
        playTimerSound();
    }

    function playTimerSound() {
        try {
            const audio = new Audio('/static/sounds/time_out.mp3');
            audio.play().catch(error => {
                console.log('타이머 소리 재생 실패:', error);
            });
        } catch (error) {
            console.log('오디오 생성 실패:', error);
        }
    }

    function startTimer() {
        if (timerInterval) {
            return; // 이미 실행 중
        }
        
        timerInterval = setInterval(() => {
            timePassed += 1;
            timeLeft = TIME_LIMIT - timePassed;
            updateTimerDisplay();
            setCircleDasharray();
            setRemainingPathColor(timeLeft);

            if (timeLeft === 0) {
                onTimesUp();
            }
        }, 1000);
        updatePlayButtonState();
    }

    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
            updatePlayButtonState();
        }
    }

    function resetTimer() {
        stopTimer();
        timePassed = 0;
        timeLeft = TIME_LIMIT;
        const minutesLabel = document.getElementById("timer-minutes");
        const secondsLabel = document.getElementById("timer-seconds");
        if (minutesLabel && secondsLabel) {
            updateTimerDisplay();
        }
        updatePlayButtonState();
        setCircleDasharray();
        setRemainingPathColor(timeLeft);
    }

    function calculateTimeFraction() {
        if (TIME_LIMIT === 0) return 1;
        const rawTimeFraction = timeLeft / TIME_LIMIT;
        return rawTimeFraction - (1 / TIME_LIMIT) * (1 - rawTimeFraction);
    }

    function setCircleDasharray() {
        const remainingPath = document.getElementById("base-timer-path-remaining");
        if (!remainingPath || TIME_LIMIT === 0) return;
        
        const circleDasharray = `${(
            calculateTimeFraction() * FULL_DASH_ARRAY
        ).toFixed(0)} ${FULL_DASH_ARRAY}`;
        remainingPath.setAttribute("stroke-dasharray", circleDasharray);
    }

    function setRemainingPathColor(timeLeft) {
        const remainingPath = document.getElementById("base-timer-path-remaining");
        if (!remainingPath) return;

        
        const { warning } = COLOR_CODES;
        remainingPath.classList.remove("green", "red");
        remainingPath.classList.add(warning.color);
        remainingPathColor = warning.color;
    }

    function setTimerTime(seconds) {
        if (seconds <= 0) {
            return;
        }
        TIME_LIMIT = seconds;
        resetTimer();
        setCircleDasharray();
        setRemainingPathColor(timeLeft);
    }

    function addTimeToTimer(secondsToAdd) {
        if (secondsToAdd <= 0) {
            return;
        }
        
        // 현재 남은 시간에 추가
        timeLeft += secondsToAdd;
        TIME_LIMIT += secondsToAdd;
        
        // 시간 표시 및 원형 진행 표시 업데이트
        updateTimerDisplay();
        setCircleDasharray();
        setRemainingPathColor(timeLeft);
    }

    function showMinutesInput() {
        if (isEditingTime || timerInterval) {
            return;
        }

        isEditingTime = true;
        const minutesLabel = document.getElementById("timer-minutes");
        if (!minutesLabel) {
            isEditingTime = false;
            return;
        }

        const currentTime = formatTime(timeLeft);
        minutesLabel.innerHTML = `
            <input type="number" 
                   id="timer-minutes-input" 
                   class="timer-time-input timer-time-input--small" 
                   value="${currentTime.minutes}" 
                   min="0"
                   max="99"
                   maxlength="2">
        `;

        const input = document.getElementById("timer-minutes-input");
        if (input) {
            input.focus();
            input.select();

            input.addEventListener("blur", function() {
                saveMinutesInput();
            });

            input.addEventListener("keydown", function(e) {
                if (e.key === "Enter" || e.keyCode === 13) {
                    e.preventDefault();
                    saveMinutesInput();
                } else if (e.key === "Escape" || e.keyCode === 27) {
                    e.preventDefault();
                    cancelTimeInput();
                }
            });
        }
    }

    function showSecondsInput() {
        if (isEditingTime || timerInterval) {
            return;
        }

        isEditingTime = true;
        const secondsLabel = document.getElementById("timer-seconds");
        if (!secondsLabel) {
            isEditingTime = false;
            return;
        }

        const currentTime = formatTime(timeLeft);
        secondsLabel.innerHTML = `
            <input type="text" 
                   id="timer-seconds-input" 
                   class="timer-time-input timer-time-input--small" 
                   value="${currentTime.seconds}" 
                   maxlength="2"
                   inputmode="numeric"
                   pattern="[0-9]*">
        `;

        const input = document.getElementById("timer-seconds-input");
        if (input) {
            input.focus();
            input.select();

            // 숫자만 입력 가능하도록 제한
            input.addEventListener("input", function(e) {
                this.value = this.value.replace(/[^0-9]/g, '');
                if (parseInt(this.value, 10) > 59) {
                    this.value = '59';
                }
            });

            // 마우스 휠 이벤트 차단
            input.addEventListener("wheel", function(e) {
                e.preventDefault();
            });

            input.addEventListener("blur", function() {
                saveSecondsInput();
            });

            input.addEventListener("keydown", function(e) {
                if (e.key === "Enter" || e.keyCode === 13) {
                    e.preventDefault();
                    saveSecondsInput();
                } else if (e.key === "Escape" || e.keyCode === 27) {
                    e.preventDefault();
                    cancelTimeInput();
                } else if (!/[0-9]/.test(e.key) && 
                          !['Backspace', 'Delete', 'Tab', 'ArrowLeft', 'ArrowRight', 'Enter', 'Escape'].includes(e.key) &&
                          e.keyCode !== 8 && e.keyCode !== 46 && e.keyCode !== 9 && 
                          e.keyCode !== 37 && e.keyCode !== 39 && e.keyCode !== 13 && e.keyCode !== 27) {
                    e.preventDefault();
                }
            });
        }
    }

    function saveMinutesInput() {
        const input = document.getElementById("timer-minutes-input");
        if (!input) {
            isEditingTime = false;
            updateTimerDisplay();
            return;
        }

        const minutes = parseInt(input.value, 10) || 0;
        const currentTime = formatTime(timeLeft);
        const seconds = parseInt(currentTime.seconds, 10) || 0;
        const totalSeconds = minutes * 60 + seconds;

        isEditingTime = false;
        
        if (totalSeconds > 0) {
            setTimerTime(totalSeconds);
        } else {
            updateTimerDisplay();
        }
    }

    function saveSecondsInput() {
        const input = document.getElementById("timer-seconds-input");
        if (!input) {
            isEditingTime = false;
            updateTimerDisplay();
            return;
        }

        let seconds = parseInt(input.value, 10) || 0;
        if (seconds > 59) {
            seconds = 59;
        }
        
        const currentTime = formatTime(timeLeft);
        const minutes = parseInt(currentTime.minutes, 10) || 0;
        const totalSeconds = minutes * 60 + seconds;

        isEditingTime = false;
        
        if (totalSeconds > 0) {
            setTimerTime(totalSeconds);
        } else {
            updateTimerDisplay();
        }
    }

    function cancelTimeInput() {
        isEditingTime = false;
        updateTimerDisplay();
    }

    function updateTimerDisplay() {
        const minutesLabel = document.getElementById("timer-minutes");
        const secondsLabel = document.getElementById("timer-seconds");
        const timeObj = formatTime(timeLeft);

        if (minutesLabel && !isEditingTime) {
            minutesLabel.textContent = timeObj.minutes;
        }
        if (secondsLabel && !isEditingTime) {
            secondsLabel.textContent = timeObj.seconds;
        }
    }

    /**
     * 타이머 초기화
     */
    function initTimer() {
        const timerApp = document.getElementById("timer-app");
        if (!timerApp) {
            return;
        }

        // 타이머 상태 초기화 (DOM 생성 전)
        stopTimer();
        timePassed = 0;
        timeLeft = TIME_LIMIT;

        const timeObj = formatTime(timeLeft);
        timerApp.innerHTML = `
            <div class="base-timer">
                <svg class="base-timer__svg" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                    <g class="base-timer__circle">
                        <circle class="base-timer__path-elapsed" cx="50" cy="50" r="45"></circle>
                        <path
                            id="base-timer-path-remaining"
                            stroke-dasharray="${FULL_DASH_ARRAY}"
                            class="base-timer__path-remaining ${remainingPathColor}"
                            d="
                                M 50, 50
                                m -45, 0
                                a 45,45 0 1,0 90,0
                                a 45,45 0 1,0 -90,0
                            "
                        ></path>
                    </g>
                </svg>
                <div class="base-timer__content">
                    <div class="base-timer__left-label">LEFT</div>
                    <div id="base-timer-label" class="base-timer__time">
                        <span id="timer-minutes" class="timer-time-part">${timeObj.minutes}</span>
                        <span class="timer-time-separator">:</span>
                        <span id="timer-seconds" class="timer-time-part">${timeObj.seconds}</span>
                    </div>
                    <div id="base-timer-play-button" class="base-timer__play-button"></div>
                </div>
            </div>
        `;
        
        // DOM 생성 후 타이머 상태 업데이트
        updateTimerDisplay();
        updatePlayButtonState();
        setCircleDasharray();
        setRemainingPathColor(timeLeft);

        // 시간 추가 버튼 이벤트 리스너 추가
        bindTimerAddButtons();

        // 분 클릭 시 분 입력 모드로 전환
        const minutesLabel = document.getElementById("timer-minutes");
        if (minutesLabel) {
            minutesLabel.addEventListener("click", function(e) {
                e.stopPropagation();
                if (!timerInterval && !isEditingTime) {
                    showMinutesInput();
                }
            });
        }

        // 초 클릭 시 초 입력 모드로 전환
        const secondsLabel = document.getElementById("timer-seconds");
        if (secondsLabel) {
            secondsLabel.addEventListener("click", function(e) {
                e.stopPropagation();
                if (!timerInterval && !isEditingTime) {
                    showSecondsInput();
                }
            });
        }

        // 재생 버튼 이벤트 리스너 추가
        const playButton = document.getElementById("base-timer-play-button");
        if (playButton) {
            playButton.addEventListener("click", function(e) {
                e.stopPropagation();
                if (timerInterval) {
                    stopTimer();
                } else {
                    if (timeLeft > 0) {
                        startTimer();
                    }
                }
            });
        }
    }



    // ============================================
    // 요리 완료 페이지 모듈
    // ============================================

    /**
     * 시간 추가 버튼 이벤트 바인딩
     */
    function bindTimerAddButtons() {
        const addButtons = document.querySelectorAll('.timer-add-btn');
        
        addButtons.forEach(button => {
            button.addEventListener('click', function() {
                const secondsToAdd = parseInt(this.dataset.seconds, 10);
                if (!isNaN(secondsToAdd) && secondsToAdd > 0) {
                    addTimeToTimer(secondsToAdd);
                    
                    // 버튼 클릭 효과 (시각적 피드백)
                    this.style.transform = 'scale(0.95)';
                    setTimeout(() => {
                        this.style.transform = '';
                    }, 150);
                }
            });
        });
    }

    /**
     * 요리 완료 페이지 초기화
     */
    function initCookingComplete() {
        const completeContainer = document.querySelector('.cooking-complete-container');
        if (!completeContainer) {
            return; 
        }

        bindChecklistEvents();
        bindCompleteButtonEvents();
    }

    /**
     * 체크리스트 이벤트 바인딩
     */
    function bindChecklistEvents() {
        const checklistItems = document.querySelectorAll('.checklist-item');
        
        checklistItems.forEach(item => {
            item.addEventListener('click', function(e) {
                e.stopPropagation();
                toggleChecklistItem(this);
            });
        });
    }

    /**
     * 체크리스트 항목 토글
     */
    function toggleChecklistItem(item) {
        const checkbox = item.querySelector('.checkbox');
        const checkmark = checkbox.querySelector('.checkmark');
        const itemText = item.querySelector('.item-text');
        
        if (item.classList.contains('checked')) {
            // 체크 해제
            item.classList.remove('checked');
            if (checkmark) {
                checkmark.style.display = 'none';
            }
            if (itemText) {
                itemText.classList.remove('highlight');
            }
        } else {
            // 체크
            item.classList.add('checked');
            if (checkmark) {
                checkmark.style.display = 'block';
            } else {
                // 체크마크가 없으면 생성 (템플릿에 이미 있지만 안전장치)
                const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svg.setAttribute('class', 'checkmark');
                svg.setAttribute('viewBox', '0 0 20 20');
                svg.setAttribute('fill', 'none');
                svg.setAttribute('aria-hidden', 'true');
                
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', 'M18.75 2.11094C18.5806 2.13969 18.3716 2.2402 18.2397 2.35645C18.1846 2.40496 15.6192 5.32492 12.5388 8.84531L6.93789 15.2459L6.83809 15.1287C6.7832 15.0642 5.60934 13.8081 4.22953 12.3373C2.23918 10.2159 1.68223 9.64391 1.53422 9.56945C1.27711 9.44016 0.834492 9.43535 0.600937 9.55934C0.179883 9.78285 0.00101563 10.0727 0.000390625 10.5327C7.8125e-05 10.7623 0.0189062 10.8468 0.107422 11.0127C0.18082 11.1502 1.18027 12.2429 3.26172 14.4611C6.65145 18.0737 6.46422 17.9004 6.97703 17.9004C7.17371 17.9004 7.27406 17.8766 7.45113 17.7881C7.6616 17.6829 8.05996 17.2368 13.7573 10.727C18.2301 5.61629 19.8602 3.72859 19.9194 3.59082C20.0289 3.33637 20.0287 2.95078 19.919 2.71746C19.8242 2.5157 19.6179 2.29227 19.4432 2.20188C19.2952 2.12539 18.9397 2.07875 18.75 2.11094Z');
                path.setAttribute('fill', '#FF7043');
                
                svg.appendChild(path);
                checkbox.appendChild(svg);
            }
            if (itemText) {
                itemText.classList.add('highlight');
            }
        }
    }

    /**
     * 완료 페이지 버튼 이벤트 바인딩
     */
    function bindCompleteButtonEvents() {
        const btnNo = document.getElementById('btnNo');
        const btnYes = document.getElementById('btnYes');
        const dataElement = document.getElementById('cooking-complete-data');
        
        if (!dataElement) {
            console.warn('cooking-complete-data 요소를 찾을 수 없습니다.');
        }

        const recipeId = dataElement ? dataElement.dataset.recipeId : null;
        const logCreateUrl = dataElement ? dataElement.dataset.logCreateUrl : null;

        // "아니오" 버튼 - 레시피 목록으로 이동
        if (btnNo) {
            btnNo.addEventListener('click', function() {
                // 체크된 재료를 소비 처리 (선택사항)
                const checkedIngredients = getCheckedIngredientIds();
                if (checkedIngredients.length > 0) {
                    consumeIngredients(checkedIngredients);
                }
                
                // 레시피 목록으로 이동
                window.location.href = '/';
            });
        }

        // "예" 버튼 - 일지 작성 페이지로 이동
        if (btnYes) {
            btnYes.addEventListener('click', function() {
                // 체크된 재료를 소비 처리 (선택사항)
                const checkedIngredients = getCheckedIngredientIds();
                if (checkedIngredients.length > 0) {
                    consumeIngredients(checkedIngredients);
                }
                
                // 일지 작성 페이지로 이동
                if (logCreateUrl && recipeId) {
                    window.location.href = `${logCreateUrl}?recipe_id=${recipeId}`;
                } else if (logCreateUrl) {
                    window.location.href = logCreateUrl;
                } else {
                    window.location.href = '/logs/create/';
                }
            });
        }
    }

    /**
     * 체크된 재료 ID 수집
     */
    function getCheckedIngredientIds() {
        const checkedItems = document.querySelectorAll('.checklist-item.checked');
        return Array.from(checkedItems)
            .map(item => item.dataset.ingredientId)
            .filter(id => id); // 유효한 ID만 반환
    }

    /**
     * 재료 소비 처리 (API 호출)
     */
    async function consumeIngredients(ingredientIds) {
        if (!ingredientIds || ingredientIds.length === 0) {
            return;
        }

        try {
            const csrfToken = getCsrfToken();
            if (!csrfToken) {
                console.warn('CSRF 토큰을 찾을 수 없습니다.');
                return;
            }
            
            // API 호출 (실제 엔드포인트에 맞게 수정 필요)
            const response = await fetch('/ingredients/api/consume/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    ingredient_ids: ingredientIds
                })
            });

            if (!response.ok) {
                console.error('재료 소비 처리 실패:', response.statusText);
            }
        } catch (error) {
            console.error('재료 소비 처리 중 오류:', error);
        }
    }

    // DOMContentLoaded 시 초기화
    document.addEventListener('DOMContentLoaded', function() {
        initCookingComplete();
    });