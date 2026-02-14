/**
 * 메인 페이지 JavaScript
 * 레시피 캐러셀, 찜한 레시피, 식재료, 일지 슬라이더 기능
 */

(function() {
    'use strict';
    
    // ========== 유틸리티 함수 ==========
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function getAccessToken() {
        const token = localStorage.getItem('access_token');
        if (token) return token;
        return getCookie('access_token');
    }

    function handleUnauthorized() {
        alert('로그인이 만료되었습니다. 다시 로그인해주세요.');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        window.location.href = '/users/login/?next=' + encodeURIComponent(window.location.pathname);
    }
    
    // 스크롤 헤더 축소 함수
    let scrollTimeout;
    let isScrolled = false;
    /** 스크롤이 실제로 일어나는 요소 (capture로 잡은 target 저장) */
    var activeScrollTarget = null;

    function getScrollY() {
        if (activeScrollTarget) {
            var y = activeScrollTarget.scrollTop;
            if (y > 0) return y;
        }
        return window.pageYOffset || window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0;
    }

    function toggleHeaderOnScroll(optionalScrollTarget) {
        clearTimeout(scrollTimeout);

        scrollTimeout = setTimeout(function() {
            var fromEl = optionalScrollTarget || activeScrollTarget || document.scrollingElement || document.documentElement;
            var y = (fromEl && fromEl.scrollTop !== undefined) ? fromEl.scrollTop : (window.pageYOffset || window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0);

            var mainHeader = document.getElementById('mainHeader');
            var scrollThreshold = 40;

            if (!mainHeader) {
                return;
            }

            var upperThreshold = scrollThreshold;
            var lowerThreshold = scrollThreshold - 30;

            if (!isScrolled) {
                if (y > upperThreshold) {
                    mainHeader.classList.add('scrolled');
                    isScrolled = true;
                }
            } else {
                if (y <= lowerThreshold) {
                    mainHeader.classList.remove('scrolled');
                    isScrolled = false;
                }
            }
        }, 16);
    }

    // 상수 정의
    const CAROUSEL_MAX_VISIBILITY = 3;
    const CAROUSEL_MAX_CARDS = 6;
    const FAVORITES_MAX_HOME = 3;  /* 홈 화면 찜한 레시피 최대 개수 */
    const DIARY_SCROLL_AMOUNT = 300;
    const CAROUSEL_DEFAULT_INDEX = 2;

    // 전역 변수
    let activeRecipeIndex = CAROUSEL_DEFAULT_INDEX;
    let recipes = [];
    let carouselDisplayCount = CAROUSEL_MAX_CARDS;

    // 찜 상태 관리
    let favoritedIds = new Set();
    let processingIds = new Set();

    /**
     * 레시피 캐러셀 초기화
     */
    function initCarousel() {
        const carousel = document.getElementById('recipeCarousel');
        const dotsContainer = document.getElementById('carouselDots');
        
        if (!carousel || !dotsContainer) {
            return;
        }

        carousel.innerHTML = '';
        dotsContainer.innerHTML = '';

        if (!recipes || recipes.length === 0) {
            carousel.innerHTML = '<p class="empty-state">추천 레시피가 없습니다.</p>';
            return;
        }

        carouselDisplayCount = Math.min(CAROUSEL_MAX_CARDS, recipes.length);
        if (activeRecipeIndex >= carouselDisplayCount) {
            activeRecipeIndex = Math.max(0, carouselDisplayCount - 1);
        }
        const difficultyMap = { 'EASY': '쉬움', 'NORMAL': '보통', 'DIFFICULT': '어려움' };
        recipes.slice(0, CAROUSEL_MAX_CARDS).forEach((recipe, index) => {
            const difficultyText = difficultyMap[recipe.difficulty] || '보통';
            const cardContainer = document.createElement('div');
            cardContainer.className = 'card-container';
            cardContainer.dataset.recipeId = recipe.id;
            cardContainer.innerHTML = `
                <div class="carousel-card">
                    <h3>${escapeHtml(recipe.name)}</h3>
                    <div class="recipe-image">
                        <img src="${escapeHtml(recipe.image)}" alt="${escapeHtml(recipe.name)}" loading="lazy">
                    </div>
                    <div class="recipe-info">
                        <p>난이도: ${escapeHtml(difficultyText)}</p>
                        <p>예상 조리시간: ${escapeHtml(recipe.cookingTime || 'N/A')}</p>
                    </div>
                </div>
            `;
            
            cardContainer.addEventListener('click', function() {
                if (index === activeRecipeIndex) {
                    const recipeId = this.dataset.recipeId;
                    if (recipeId) {
                        window.location.href = `/recipes/${recipeId}/cooking/`;
                    }
                }
            });
            
            carousel.appendChild(cardContainer);
        });

        for (let i = 0; i < carouselDisplayCount; i++) {
            const dot = document.createElement('button');
            dot.className = 'carousel-dot';
            dot.setAttribute('aria-label', `${i + 1}번째 레시피`);
            dot.addEventListener('click', () => setActiveRecipe(i));
            dotsContainer.appendChild(dot);
        }
        
        createCarouselNavigation(carousel);
        updateCarousel();
    }

    function createCarouselNavigation(carousel) {
        const leftBtn = document.createElement('button');
        leftBtn.className = 'carousel-nav left';
        leftBtn.setAttribute('aria-label', '이전 레시피');
        leftBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"></path></svg>';
        leftBtn.addEventListener('click', () => setActiveRecipe(Math.max(0, activeRecipeIndex - 1)));
        
        const rightBtn = document.createElement('button');
        rightBtn.className = 'carousel-nav right';
        rightBtn.setAttribute('aria-label', '다음 레시피');
        rightBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"></path></svg>';
        rightBtn.addEventListener('click', () => setActiveRecipe(Math.min(carouselDisplayCount - 1, activeRecipeIndex + 1)));
        
        carousel.appendChild(leftBtn);
        carousel.appendChild(rightBtn);
    }

    function setActiveRecipe(index) {
        if (index < 0 || index >= carouselDisplayCount) return;
        activeRecipeIndex = index;
        updateCarousel();
    }

    function updateCarousel() {
        const cardContainers = document.querySelectorAll('.card-container');
        const dots = document.querySelectorAll('.carousel-dot');
        const leftBtn = document.querySelector('.carousel-nav.left');
        const rightBtn = document.querySelector('.carousel-nav.right');
        
        if (!cardContainers.length) return;

        cardContainers.forEach((card, i) => {
            const offset = (activeRecipeIndex - i) / 3;
            const direction = Math.sign(activeRecipeIndex - i);
            const absOffset = Math.abs(activeRecipeIndex - i) / 3;
            const isActive = i === activeRecipeIndex ? 1 : 0;
            
            card.style.setProperty('--active', isActive);
            card.style.setProperty('--offset', offset);
            card.style.setProperty('--direction', direction);
            card.style.setProperty('--abs-offset', absOffset);
            card.style.pointerEvents = isActive ? 'auto' : 'none';
            card.style.opacity = Math.abs(activeRecipeIndex - i) >= CAROUSEL_MAX_VISIBILITY ? '0' : '1';
            card.style.display = Math.abs(activeRecipeIndex - i) > CAROUSEL_MAX_VISIBILITY ? 'none' : 'block';
            
            card.style.transform = `
                rotateY(${offset * 50}deg) 
                scaleY(${1 + absOffset * -0.4})
                translateZ(${absOffset * -30}rem)
                translateX(${direction * -5}rem)
            `;
            card.style.filter = `blur(${absOffset * 0.3}rem)`;
            
            const cardElement = card.querySelector('.carousel-card');
            if (cardElement) {
                const brightness = 100 - absOffset * 10;
                cardElement.style.backgroundColor = `hsl(0deg, 0%, ${Math.max(brightness, 90)}%)`;
            }
            
            const h3 = card.querySelector('h3');
            const recipeImage = card.querySelector('.recipe-image');
            const recipeInfo = card.querySelector('.recipe-info');
            if (h3) h3.style.opacity = isActive;
            if (recipeImage) recipeImage.style.opacity = isActive;
            if (recipeInfo) recipeInfo.style.opacity = isActive;
        });
        
        dots.forEach((dot, i) => {
            dot.classList.toggle('active', i === activeRecipeIndex);
        });
        
        if (leftBtn) leftBtn.style.display = activeRecipeIndex > 0 ? 'flex' : 'none';
        if (rightBtn) rightBtn.style.display = activeRecipeIndex < carouselDisplayCount - 1 ? 'flex' : 'none';
    }

    /**
     * ========== [추가] 찜 상태 로드 및 별 아이콘 업데이트 ==========
     */
    async function loadFavoriteStatus() {
        console.log('========================================');
        console.log('💛 [메인] loadFavoriteStatus 시작');
        console.log('========================================');
        
        const token = getAccessToken();
        console.log('🔑 토큰:', token ? '있음' : '없음');
        
        if (!token) {
            console.log('⚠️ 비로그인 사용자');
            return;
        }

        try {
            console.log('📡 GET /recipes/api/favorites/');
            
            const response = await fetch('/recipes/api/favorites/', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            console.log('📥 응답 상태:', response.status);

            if (response.status === 401) {
                console.error('❌ 인증 만료');
                handleUnauthorized();
                return;
            }

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ 응답 실패:', response.status, errorText);
                return;
            }
            
            const data = await response.json();
            console.log('✅ 응답 데이터:', data);
            
            // pagination 응답 처리
            let favoritesList = [];
            if (Array.isArray(data)) {
                favoritesList = data;
            } else if (data && data.results) {
                favoritesList = data.results;
            }
            
            // favoritedIds 업데이트
            favoritedIds.clear();
            favoritesList.forEach(item => {
                const recipe = item.recipe || item;
                const recipeId = recipe.recipe_id || recipe.id;
                if (recipeId) {
                    favoritedIds.add(recipeId);
                }
            });
            
            console.log('💛 찜한 ID:', Array.from(favoritedIds));
            
            // 별 아이콘 업데이트
            updateFavoriteStars();
            console.log('========================================');
            
        } catch (error) {
            console.error('========================================');
            console.error('❌ loadFavoriteStatus 오류:', error);
            console.error('========================================');
        }
    }

    /**
     * 별 아이콘 상태 업데이트
     */
    function updateFavoriteStars() {
        document.querySelectorAll('.favorite-btn').forEach(btn => {
            const recipeId = parseInt(btn.dataset.id);
            
            if (processingIds.has(recipeId)) {
                return;
            }
            
            if (favoritedIds.has(recipeId)) {
                btn.classList.remove('inactive');
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
                btn.classList.add('inactive');
            }
        });
    }

    /**
     * ========== [완전 재구현] 찜한 레시피 초기화 - API에서 불러오기 ==========
     */
    async function initFavoriteRecipes() {
        console.log('========================================');
        console.log('💛 [메인] initFavoriteRecipes 시작');
        console.log('========================================');
        
        const container = document.getElementById('favoriteRecipes');
        if (!container) {
            console.warn('⚠️ favoriteRecipes 컨테이너를 찾을 수 없습니다');
            return;
        }

        const token = getAccessToken();
        console.log('🔑 토큰:', token ? '있음' : '없음');
        
        if (!token) {
            console.log('⚠️ 비로그인 사용자');
            container.innerHTML = '<p class="empty-state">로그인이 필요합니다.</p>';
            return;
        }

        try {
            console.log('📡 GET /recipes/api/favorites/');
            
            const response = await fetch('/recipes/api/favorites/', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            console.log('📥 응답 상태:', response.status);

            if (response.status === 401) {
                console.error('❌ 인증 만료');
                handleUnauthorized();
                return;
            }

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ 응답 실패:', response.status, errorText);
                throw new Error(`찜 목록 로드 실패: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('✅ 응답 데이터:', data);
            console.log('📊 타입:', Array.isArray(data) ? '배열' : typeof data);
            
            // ========== [수정] pagination 응답 처리 ==========
            let favoritesList = [];
            
            // 배열인 경우 (pagination 없음)
            if (Array.isArray(data)) {
                favoritesList = data;
                console.log('📦 배열 응답');
            }
            // 객체인 경우 (pagination 있음)
            else if (data && typeof data === 'object') {
                // results 배열 추출
                if (Array.isArray(data.results)) {
                    favoritesList = data.results;
                    console.log('📦 pagination 응답 - count:', data.count);
                } else {
                    console.error('❌ results 필드가 배열이 아님:', data);
                    throw new Error('응답 형식 오류: results가 없거나 배열이 아님');
                }
            } else {
                console.error('❌ 잘못된 응답 형식:', data);
                throw new Error('응답 형식 오류');
            }
            
            console.log('📊 찜한 레시피 개수:', favoritesList.length);
            
            if (favoritesList.length === 0) {
                console.log('ℹ️ 찜한 레시피 0개');
                container.innerHTML = '<p class="empty-state">찜한 레시피가 없습니다.</p>';
                return;
            }
            
            console.log('🔄 레시피 카드 생성 시작');
            container.innerHTML = '';

            // 홈 화면에는 최대 3개만 표시
            const favoritesToShow = favoritesList.slice(0, FAVORITES_MAX_HOME);
            // 찜한 레시피 렌더링
            favoritesToShow.forEach((item, index) => {
                console.log(`  [${index}] 처리 중:`, item);
                
                // recipe 객체 추출
                let recipe = null;
                if (item.recipe && typeof item.recipe === 'object') {
                    recipe = item.recipe;
                } else if (item.recipe_id || item.title) {
                    recipe = item;
                } else {
                    console.warn(`  [${index}] recipe 없음, 건너뜀`);
                    return;
                }
                
                // recipe_id 정규화
                const recipeId = recipe.recipe_id || recipe.id;
                if (!recipeId) {
                    console.warn(`  [${index}] recipe_id 없음, 건너뜀`);
                    return;
                }
                
                // 찜 상태 저장
                favoritedIds.add(recipeId);
                
                // 레시피 이름과 이미지
                const recipeName = recipe.display_title || recipe.title_ko || recipe.title || '레시피';
                const recipeImage = recipe.image_url || recipe.image || '/static/images/default-recipe.jpg';
                
                console.log(`  [${index}] 렌더링: ${recipeName} (ID: ${recipeId})`);
                
                // 카드 생성
                const card = document.createElement('div');
                card.className = 'recipe-card';
                card.dataset.recipeId = recipeId;
                card.innerHTML = `
                    <div class="recipe-image-small">
                        <img src="${escapeHtml(recipeImage)}" 
                             alt="${escapeHtml(recipeName)}" 
                             loading="lazy"
                             onerror="this.src='/static/images/default-recipe.jpg'">
                    </div>
                    <span class="recipe-name">${escapeHtml(recipeName)}</span>
                    <button class="favorite-btn active" 
                            data-id="${recipeId}" 
                            aria-label="찜 취소">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                        </svg>
                    </button>
                `;
                
                // 카드 클릭 이벤트 (레시피 조리 모드로 이동)
                card.addEventListener('click', function(e) {
                    if (e.target.closest('.favorite-btn')) {
                        return;
                    }
                    window.location.href = `/recipes/${recipeId}/cooking/`;
                });
                
                // 찜 버튼 이벤트
                const favoriteBtn = card.querySelector('.favorite-btn');
                favoriteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    toggleFavorite(recipeId, favoriteBtn, card);
                });
                
                container.appendChild(card);
            });
            
            console.log('💛 찜한 ID:', Array.from(favoritedIds));
            console.log('========================================');
            
        } catch (error) {
            console.error('========================================');
            console.error('❌ initFavoriteRecipes 오류:', error);
            console.error('========================================');
            container.innerHTML = '<p class="empty-state">찜한 레시피를 불러오지 못했습니다.</p>';
        }
    }

    /**
     * ========== [수정] 찜하기 토글 - toggle API 사용 ==========
     */
    async function toggleFavorite(recipeId, button, card = null) {
        if (processingIds.has(recipeId)) {
            console.log('⏳ 이미 처리 중:', recipeId);
            return;
        }
        
        const wasLiked = favoritedIds.has(recipeId);
        console.log('========================================');
        console.log('⭐ [메인] 찜 클릭:', recipeId, wasLiked ? '취소' : '추가');

        const token = getAccessToken();
        const csrfToken = getCookie('csrftoken');
        
        if (!token) {
            alert('로그인이 필요합니다');
            window.location.href = '/users/login/?next=' + encodeURIComponent(window.location.pathname);
            return;
        }

        processingIds.add(recipeId);
        button.disabled = true;
        button.style.opacity = '0.6';

        try {
            console.log('📡 POST /recipes/api/favorites/toggle/');
            console.log('📤 Body:', { recipe_id: recipeId });
            
            const response = await fetch('/recipes/api/favorites/toggle/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ recipe_id: recipeId })
            });
            
            console.log('📥 응답 상태:', response.status);
            
            if (response.status === 401) {
                console.error('❌ 인증 만료');
                handleUnauthorized();
                return;
            }
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ 응답 실패:', response.status, errorText);
                throw new Error(`API 오류: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('✅ 응답 데이터:', data);
            
            // 서버 응답에 따라 상태 업데이트
            if (data.is_favorite) {
                favoritedIds.add(recipeId);
                button.classList.add('active');
                console.log('✅ 찜 추가 완료');
            } else {
                favoritedIds.delete(recipeId);
                button.classList.remove('active');
                console.log('✅ 찜 취소 완료');
                
                // 메인 화면 찜한 레시피 목록에서 카드 제거
                if (card) {
                    card.style.transition = 'opacity 0.3s, transform 0.3s';
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.8)';
                    
                    setTimeout(() => {
                        card.remove();
                        
                        // 모든 카드가 삭제되었으면 빈 상태 표시
                        const container = document.getElementById('favoriteRecipes');
                        if (container && container.children.length === 0) {
                            container.innerHTML = '<p class="empty-state">찜한 레시피가 없습니다.</p>';
                        }
                    }, 300);
                }
            }
            
            console.log('========================================');
            
        } catch (error) {
            console.error('========================================');
            console.error('❌ 찜 처리 오류:', error);
            console.error('========================================');
            alert('찜 처리 중 오류가 발생했습니다\n\n' + error.message);
        } finally {
            processingIds.delete(recipeId);
            button.disabled = false;
            button.style.opacity = '1';
        }
    }

    /**
     * 식재료 초기화
     */
    function initIngredients() {
        const container = document.getElementById('ingredientsGrid');
        if (!container) return;

        let ingredients = [];
        try {
            const dataScript = document.getElementById('ingredients-data');
            if (dataScript) {
                ingredients = JSON.parse(dataScript.textContent);
            } else {
                const parentContainer = container.closest('.ingredients-container');
                if (parentContainer && parentContainer.querySelector('[data-ingredients]')) {
                    ingredients = JSON.parse(parentContainer.querySelector('[data-ingredients]').dataset.ingredients);
                }
            }
        } catch (e) {
            console.error('식재료 데이터 파싱 오류:', e);
            ingredients = [];
        }
        
        if (ingredients.length === 0) {
            const emptyState = document.createElement('div');
            emptyState.className = 'ingredient-empty-state';
            emptyState.textContent = '등록된 식재료가 없습니다.';
            container.appendChild(emptyState);
            return;
        }

        ingredients.sort((a, b) => {
            const getDaysValue = (daysLeft) => {
                if (!daysLeft || daysLeft === '-' || daysLeft === null || daysLeft === undefined) return null;
                if (daysLeft === 'D-Day') return 0;
                if (typeof daysLeft === 'string' && daysLeft.startsWith('D+')) {
                    return -parseInt(daysLeft.substring(2)) || null;
                }
                if (typeof daysLeft === 'string' && daysLeft.startsWith('D-')) {
                    return parseInt(daysLeft.substring(2)) || null;
                }
                return null;
            };
            
            const daysA = getDaysValue(a.daysLeft);
            const daysB = getDaysValue(b.daysLeft);
            
            if (daysA !== null && daysB === null) return -1;
            if (daysA === null && daysB !== null) return 1;
            
            if (daysA !== null && daysB !== null) {
                if (daysA < daysB) return -1;
                if (daysA > daysB) return 1;
            }
            
            const nameA = a.name || '';
            const nameB = b.name || '';
            return nameA.localeCompare(nameB, 'ko');
        });

        ingredients = ingredients.slice(0, 8);

        ingredients.forEach(ingredient => {
            const btn = document.createElement('button');
            const daysLeftDisplay = ingredient.daysLeft || '-';
            btn.className = 'ingredient-btn';
            btn.setAttribute('aria-label', `${ingredient.name} (${daysLeftDisplay})`);
            btn.innerHTML = `
                <div class="ingredient-icon">
                    <img src="${escapeHtml(ingredient.image)}" alt="${escapeHtml(ingredient.name)}" loading="lazy">
                </div>
                <div class="ingredient-info">
                    <span class="ingredient-name">${escapeHtml(ingredient.name)}</span>
                    <span class="ingredient-days">${escapeHtml(daysLeftDisplay)}</span>
                </div>
            `;
            container.appendChild(btn);
        });
    }

    /**
     * 일지 슬라이더 초기화
     */
    function initDiarySlider() {
        const slider = document.getElementById('diarySlider');
        const prevBtn = document.getElementById('diaryPrev');
        const nextBtn = document.getElementById('diaryNext');
        
        if (!slider) return;

        const scriptEl = document.getElementById('diaryEntriesData');
        const diaryEntries = scriptEl && scriptEl.textContent.trim() ? JSON.parse(scriptEl.textContent) : [];
        
        if (diaryEntries.length === 0) {
            slider.classList.add('empty');
            const emptyState = document.createElement('div');
            emptyState.className = 'diary-empty-state';
            emptyState.textContent = '등록된 일지가 없습니다.';
            slider.appendChild(emptyState);
            if (prevBtn) prevBtn.style.display = 'none';
            if (nextBtn) nextBtn.style.display = 'none';
            return;
        }

        diaryEntries.forEach(entry => {
            const card = document.createElement('div');
            card.className = 'diary-card';
            card.innerHTML = `
                <div class="diary-card-inner" data-log-id="${entry.id}">
                    <div class="diary-image">
                        <img src="${escapeHtml(entry.image)}" alt="${escapeHtml(entry.title)}" loading="lazy">
                    </div>
                    <div class="diary-title">${escapeHtml(entry.title)}</div>
                    <div class="diary-date">${escapeHtml(entry.date)}</div>
                </div>
            `;
            card.addEventListener('click', () => {
                window.location.href = `/logs/${entry.id}/`;
            });
            slider.appendChild(card);
        });
        
        function checkScroll() {
            if (!slider) return;
            const { scrollLeft, scrollWidth, clientWidth } = slider;
            if (prevBtn) prevBtn.style.display = scrollLeft > 0 ? 'flex' : 'none';
            if (nextBtn) nextBtn.style.display = scrollLeft < scrollWidth - clientWidth - 10 ? 'flex' : 'none';
        }
        
        function scroll(direction) {
            if (!slider) return;
            slider.scrollLeft += direction === 'left' ? -DIARY_SCROLL_AMOUNT : DIARY_SCROLL_AMOUNT;
            setTimeout(checkScroll, 300);
        }
        
        if (prevBtn) prevBtn.addEventListener('click', (e) => { e.preventDefault(); scroll('left'); e.target.closest('button')?.blur(); });
        if (nextBtn) nextBtn.addEventListener('click', (e) => { e.preventDefault(); scroll('right'); e.target.closest('button')?.blur(); });
        slider.addEventListener('scroll', checkScroll);
        
        checkScroll();
    }

    /**
     * 검색창 초기화 - 레시피 탭으로 이동하며 검색
     */
    function initSearchInput() {
        const searchInput = document.getElementById('searchInput');
        const searchIconBtn = document.getElementById('searchIconBtn');
        const mainHeader = document.getElementById('mainHeader');
        if (!searchInput) return;

        const goToRecipeSearch = (focusSearch) => {
            const keyword = (searchInput.value || '').trim();
            const baseUrl = searchInput.dataset.recipeListUrl || '/recipes/';
            const params = new URLSearchParams();
            if (keyword) params.set('q', keyword);
            if (focusSearch) params.set('focus', 'search');
            const query = params.toString();
            const url = query ? `${baseUrl}?${query}` : baseUrl;
            window.location.href = url;
        };

        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                goToRecipeSearch(false);
            }
        });

        if (searchIconBtn && mainHeader) {
            searchIconBtn.addEventListener('click', () => {
                if (mainHeader.classList.contains('scrolled')) {
                    goToRecipeSearch(true);
                } else {
                    searchInput.focus();
                }
            });
        }
    }

    /**
     * 플로팅 추가 버튼 초기화
     */
    function initFloatingButton() {
        const btn = document.getElementById('addRecipeBtn');
        if (!btn) return;
        
        btn.addEventListener('click', () => {
            const addUrl = btn.dataset.addUrl || '/ingredients/add/';
            window.location.href = addUrl;
        });
    }

    /**
     * HTML 이스케이프
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 레시피 데이터 설정
     */
    function setRecipes(recipeData) {
        recipes = recipeData || [];
        if (document.getElementById('recipeCarousel')) {
            initCarousel();
        }
    }

    /**
     * 헤더 고정 시 컨테이너 패딩 조정
     */
    function adjustContainerPadding() {
        const header = document.querySelector('.header');
        const appContainer = document.querySelector('.app-container');
        
        if (header && appContainer) {
            const headerHeight = header.offsetHeight;
            appContainer.style.paddingTop = headerHeight + 'px';
        }
    }

    // DOM 로드 완료 시 초기화
    document.addEventListener('DOMContentLoaded', async () => {
        console.log('🚀 [메인] DOMContentLoaded');
        
        // 먼저 찜 상태 로드
        await loadFavoriteStatus();
        
        const recipeDataElement = document.getElementById('recipeData');
        if (recipeDataElement) {
            const recipeData = JSON.parse(recipeDataElement.textContent);
            setRecipes(recipeData);
        }

        initCarousel();
        await initFavoriteRecipes();  // API에서 불러옴
        initIngredients();
        initDiarySlider();
        initSearchInput();
        initFloatingButton();
        
        // 찜 상태 다시 업데이트 (찜한 레시피 카드가 생성된 후)
        updateFavoriteStars();
        
        adjustContainerPadding();
        window.addEventListener('resize', adjustContainerPadding);
        
        setTimeout(function() {
            var mainHeader = document.getElementById('mainHeader');
            
            if (!mainHeader) {
                return;
            }
            
            var scrollHandler = function(e) {
                // 헤더는 페이지(윈도우) 스크롤에만 반응. 일지 슬라이더 등 내부 스크롤은 무시
                var t = e.target;
                if (t !== document && t !== document.documentElement && t !== document.body && t !== document.scrollingElement) {
                    return;
                }
                activeScrollTarget = e.target;
                toggleHeaderOnScroll(e.target);
            };
            window.addEventListener('scroll', scrollHandler, { passive: true });
            document.addEventListener('scroll', scrollHandler, { passive: true, capture: true });

            mainHeader.classList.remove('scrolled');
            isScrolled = false;

            toggleHeaderOnScroll();
        }, 100);
    });

    // 전역으로 내보내기
    window.MainPage = {
        setRecipes: setRecipes,
        setActiveRecipe: setActiveRecipe,
        toggleHeaderOnScroll: toggleHeaderOnScroll,
        refreshFavorites: initFavoriteRecipes  // 외부에서 찜 목록 새로고침 가능
    };

})();