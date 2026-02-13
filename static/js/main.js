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
    
    // 스크롤 헤더 축소 함수
    let scrollTimeout;
    let isScrolled = false;
    
    function toggleHeaderOnScroll() {
        clearTimeout(scrollTimeout);
        
        scrollTimeout = setTimeout(function() {
            var y = window.pageYOffset || window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0;
            
            var mainHeader = document.getElementById('mainHeader');
            var searchIconBtn = document.getElementById('searchIconBtn');
            var scrolledNotification = document.querySelector('.header-scrolled-notification');
            var scrollThreshold = 40;
            
            if (!mainHeader) {
                console.error('mainHeader를 찾을 수 없습니다');
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
    const DIARY_SCROLL_AMOUNT = 150;
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
            console.warn('캐러셀 요소를 찾을 수 없습니다.');
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
            // ========== [추가] recipe_id를 data 속성으로 저장 ==========
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
            
            // ========== [추가] 카드 클릭 이벤트 ==========
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
            // ========== [수정] 활성 카드만 클릭 가능 ==========
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
     * 찜한 레시피 초기화
     */
    function initFavoriteRecipes() {
        const container = document.getElementById('favoriteRecipes');
        if (!container) return;

        const favoriteRecipes = container.dataset.recipes ? JSON.parse(container.dataset.recipes) : [];
        
        if (favoriteRecipes.length === 0) {
            container.innerHTML = '<p class="empty-state">찜한 레시피가 없습니다.</p>';
            return;
        }

        favoriteRecipes.forEach(recipe => {
            favoritedIds.add(recipe.id);
            
            const card = document.createElement('div');
            card.className = 'recipe-card';
            card.innerHTML = `
                <div class="recipe-image-small">
                    <img src="${escapeHtml(recipe.image)}" alt="${escapeHtml(recipe.name)}" loading="lazy">
                </div>
                <span class="recipe-name">${escapeHtml(recipe.name)}</span>
                <button class="favorite-btn ${recipe.isFavorite ? 'active' : ''}" data-id="${recipe.id}" aria-label="찜하기">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                    </svg>
                </button>
            `;
            
            const favoriteBtn = card.querySelector('.favorite-btn');
            favoriteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleFavorite(recipe.id, favoriteBtn);
            });
            
            container.appendChild(card);
        });
    }

    /**
     * 찜하기 토글
     */
    async function toggleFavorite(recipeId, button) {
        if (processingIds.has(recipeId)) {
            console.log('⏳ 이미 처리 중:', recipeId);
            return;
        }
        
        const isLiked = favoritedIds.has(recipeId);
        console.log('⭐ 찜 클릭:', recipeId, isLiked ? '취소' : '추가');

        const token = getAccessToken();
        const csrfToken = getCookie('csrftoken');
        
        if (!token) {
            alert('로그인이 필요합니다');
            window.location.href = '/users/login/';
            return;
        }

        processingIds.add(recipeId);
        button.disabled = true;
        button.style.opacity = '0.6';

        try {
            if (isLiked) {
                const response = await fetch('/recipes/api/favorites/remove/', {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`,
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ recipe_id: recipeId })
                });
                
                if (response.ok) {
                    favoritedIds.delete(recipeId);
                    button.classList.remove('active');
                    console.log('✅ 찜 취소 성공');
                } else {
                    throw new Error(`찜 취소 실패: ${response.status}`);
                }
            } else {
                const response = await fetch('/recipes/api/favorites/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`,
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ recipe_id: recipeId })
                });
                
                if (response.ok) {
                    favoritedIds.add(recipeId);
                    button.classList.add('active');
                    console.log('✅ 찜 추가 성공');
                } else {
                    const errorText = await response.text();
                    console.error('❌ 찜 추가 실패:', response.status, errorText);
                    throw new Error(`찜 추가 실패: ${response.status}`);
                }
            }
        } catch (error) {
            console.error('❌ 찜 처리 오류:', error);
            alert('찜 처리 중 오류가 발생했습니다\n' + error.message);
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
            console.log('식재료 데이터:', ingredients);
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
            btn.addEventListener('click', () => {
                // TODO: 식재료 상세        
            });
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

        const diaryEntries = slider.dataset.entries ? JSON.parse(slider.dataset.entries) : [];
        
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
                <div class="diary-card-inner">
                    <div class="diary-image">
                        <img src="${escapeHtml(entry.image)}" alt="${escapeHtml(entry.title)}" loading="lazy">
                    </div>
                    <div class="diary-title">${escapeHtml(entry.title)}</div>
                    <div class="diary-date">${escapeHtml(entry.date)}</div>
                </div>
            `;
            card.addEventListener('click', () => {
                // TODO: 일지 상세 페이지로 이동
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
        
        if (prevBtn) prevBtn.addEventListener('click', () => scroll('left'));
        if (nextBtn) nextBtn.addEventListener('click', () => scroll('right'));
        slider.addEventListener('scroll', checkScroll);
        
        checkScroll();
    }

    /**
     * 플로팅 추가 버튼 초기화
     */
    function initFloatingButton() {
        const btn = document.getElementById('addRecipeBtn');
        if (!btn) return;
        
        btn.addEventListener('click', () => {
            // TODO: 레시피 추가 페이지로 이동
            console.log('레시피 추가 기능');
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
    document.addEventListener('DOMContentLoaded', () => {
        const recipeDataElement = document.getElementById('recipeData');
        if (recipeDataElement) {
            const recipeData = JSON.parse(recipeDataElement.textContent);
            setRecipes(recipeData);
        }

        initCarousel();
        initFavoriteRecipes();
        initIngredients();
        initDiarySlider();
        initFloatingButton();
        
        adjustContainerPadding();
        window.addEventListener('resize', adjustContainerPadding);
        
        setTimeout(function() {
            var mainHeader = document.getElementById('mainHeader');
            var searchIconBtn = document.getElementById('searchIconBtn');
            
            if (!mainHeader) {
                console.error('mainHeader를 찾을 수 없습니다');
                return;
            }
            
            console.log('✅ 헤더 스크롤 이벤트 초기화 완료');
            console.log('현재 스크롤 위치:', window.pageYOffset || window.scrollY || 0);
            
            var scrollHandler = function(e) {
                toggleHeaderOnScroll();
            };
            
            window.addEventListener('scroll', scrollHandler, { passive: true });
            document.addEventListener('scroll', scrollHandler, { passive: true });
            document.documentElement.addEventListener('scroll', scrollHandler, { passive: true });
            document.body.addEventListener('scroll', scrollHandler, { passive: true });
            
            console.log('✅ 스크롤 이벤트 리스너 추가됨');
            
            mainHeader.classList.remove('scrolled');
            isScrolled = false;
            
            toggleHeaderOnScroll();
            
            var scrollTestCount = 0;
            var originalToggle = toggleHeaderOnScroll;
            window.testScroll = function() {
                scrollTestCount++;
                var y = window.pageYOffset || window.scrollY || 0;
                console.log('스크롤 이벤트 발생 #' + scrollTestCount + ', 위치:', y);
                originalToggle();
            };
            
            window.testHeaderScroll = function() {
                console.log('테스트: 헤더 상태 강제 변경');
                mainHeader.classList.toggle('scrolled');
                console.log('헤더에 scrolled 클래스 있음?', mainHeader.classList.contains('scrolled'));
            };
            
            console.log('💡 테스트: 콘솔에서 testHeaderScroll() 실행하면 헤더 상태 변경 확인 가능');
        }, 100);
    });

    // 전역으로 내보내기
    window.MainPage = {
        setRecipes: setRecipes,
        setActiveRecipe: setActiveRecipe,
        toggleHeaderOnScroll: toggleHeaderOnScroll
    };

})();