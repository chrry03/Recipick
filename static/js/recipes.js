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

    /**
     * 레시피 목록 페이지 초기화
     */
    function initRecipeList() {
        const recommendBtn = document.getElementById('get-recommendations-btn');
        const searchInput = document.getElementById('recipe-search-input');
        const searchBtn = document.getElementById('search-btn');
        const spinner = document.getElementById('loading-spinner');
        const resultsContainer = document.getElementById('recipe-recommendations');
        
        if (!resultsContainer) {
            return;
        }

        /**
         * 검색 수행
         */
        async function performSearch() {
            const query = searchInput.value.trim();
            if (!query) {
                return;
            }
            
            spinner.classList.add('show');
            resultsContainer.innerHTML = '';
            
            try {
                const data = await searchRecipes(query);
                renderSearchResults(data);
            } catch (error) {
                console.error('검색 실패:', error);
                showErrorMessage('검색에 실패했습니다.');
            } finally {
                spinner.classList.remove('show');
            }
        }

        /**
         * 검색 결과 렌더링
         */
        function renderSearchResults(data) {
            if (!data.recipes || data.recipes.length === 0) {
                resultsContainer.innerHTML = '<div class="empty-state"><p>검색 결과가 없습니다.</p></div>';
                return;
            }
            
            let html = '<div class="recommendation-section">';
            html += `<h2 class="section-title">검색 결과 (${data.count}개)</h2>`;
            html += '<div class="recipe-grid">';
            
            data.recipes.forEach(recipe => {
                html += createRecipeCard(recipe);
            });
            
            html += '</div></div>';
            resultsContainer.innerHTML = html;
            
            attachRecipeCardListeners();
            attachImageErrorHandlers();
        }

        /**
         * 에러 메시지 표시
         */
        function showErrorMessage(message) {
            resultsContainer.innerHTML = `<div class="empty-state"><p>${message}</p></div>`;
        }

        /**
         * 추천 버튼 클릭 핸들러
         */
        async function handleRecommendClick() {
            recommendBtn.disabled = true;
            spinner.classList.add('show');
            resultsContainer.innerHTML = '';
            
            try {
                const data = await getRecipeRecommendations([], true, true);
                renderRecipeRecommendations(data);
                attachRecipeCardListeners();
                attachImageErrorHandlers();
            } catch (error) {
                console.error('추천 실패:', error);
                showErrorMessage('레시피 추천에 실패했습니다.<br>식재료를 등록했는지 확인해주세요.');
            } finally {
                spinner.classList.remove('show');
                recommendBtn.disabled = false;
            }
        }

        /**
         * 검색 버튼 클릭 핸들러
         */
        function handleSearchClick() {
            performSearch();
        }

        /**
         * 검색 입력 키보드 핸들러
         */
        function handleSearchKeypress(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                performSearch();
            }
        }

        /**
         * 검색 버튼 키보드 핸들러
         */
        function handleSearchBtnKeypress(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                performSearch();
            }
        }

        // 이벤트 리스너 등록
        if (recommendBtn) {
            recommendBtn.addEventListener('click', handleRecommendClick);
        }
        
        if (searchBtn) {
            searchBtn.addEventListener('click', handleSearchClick);
            searchBtn.addEventListener('keypress', handleSearchBtnKeypress);
        }
        
        if (searchInput) {
            searchInput.addEventListener('keypress', handleSearchKeypress);
        }
        
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
    // 레시피 단계 네비게이션 모듈
    // ============================================

    /**
     * RecipeStepNavigator 클래스
     * 레시피 단계 네비게이션을 관리하는 클래스
     */
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
                console.log('마지막 단계입니다.');
                return;
            }

            const nextStep = this.currentStep + 1;
            this._navigateToStep(nextStep);
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
            window.location.href = '/main/';
        }

        _updateButtonStates() {
            const nextBtn = document.querySelector('.btn-next');

            if (nextBtn) {
                if (this.currentStep >= this.totalSteps) {
                    nextBtn.disabled = true;
                    nextBtn.classList.add('disabled');
                } else {
                    nextBtn.disabled = false;
                    nextBtn.classList.remove('disabled');
                }
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
