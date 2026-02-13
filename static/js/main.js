/**
 * 메인 페이지 JavaScript
 * 레시피 캐러셀, 찜한 레시피, 식재료, 일지 슬라이더 기능
 */

(function() {
    'use strict';
    
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
            var scrollThreshold = 40; // 스크롤 임계값 (px)
            
            if (!mainHeader) {
                console.error('mainHeader를 찾을 수 없습니다');
                return;
            }
            
            // 히스테리시스 적용: 불안정한 전환 방지
            var upperThreshold = scrollThreshold; // 위쪽 임계값 (80px)
            var lowerThreshold = scrollThreshold - 30; // 아래쪽 임계값 (50px)
            

            if (!isScrolled) {
                if (y > upperThreshold) {
                    mainHeader.classList.add('scrolled');
                    isScrolled = true;
                    // console.log('헤더 축소/ 스크롤 위치:', y, 'px');
                }
            } else {
                if (y <= lowerThreshold) {
                    mainHeader.classList.remove('scrolled');
                    isScrolled = false;
                    // console.log('헤더 확장/ 스크롤 위치:', y, 'px');
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
    let carouselDisplayCount = CAROUSEL_MAX_CARDS; // 캐러셀에 표시할 카드 수 (최대 6)

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

        // 기존 카드·도트 제거 후 다시 생성
        carousel.innerHTML = '';
        dotsContainer.innerHTML = '';

        // 레시피 데이터가 없으면 종료
        if (!recipes || recipes.length === 0) {
            carousel.innerHTML = '<p class="empty-state">추천 레시피가 없습니다.</p>';
            return;
        }

        // 카드 생성 (최대 6개만 표시)
        carouselDisplayCount = Math.min(CAROUSEL_MAX_CARDS, recipes.length);
        if (activeRecipeIndex >= carouselDisplayCount) {
            activeRecipeIndex = Math.max(0, carouselDisplayCount - 1);
        }
        const difficultyMap = { 'EASY': '쉬움', 'NORMAL': '보통', 'DIFFICULT': '어려움' };
        recipes.slice(0, CAROUSEL_MAX_CARDS).forEach((recipe, index) => {
            const difficultyText = difficultyMap[recipe.difficulty] || '보통';
            const cardContainer = document.createElement('div');
            cardContainer.className = 'card-container';
            cardContainer.style.cursor = 'pointer';
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
            cardContainer.addEventListener('click', () => {
                if (index === activeRecipeIndex) {
                    window.location.href = '/recipes/' + recipe.id + '/cooking/';
                }
            });
            carousel.appendChild(cardContainer);
        });

        // 도트 생성 (최대 6개만)
        for (let i = 0; i < carouselDisplayCount; i++) {
            const dot = document.createElement('button');
            dot.className = 'carousel-dot';
            dot.setAttribute('aria-label', `${i + 1}번째 레시피`);
            dot.addEventListener('click', () => setActiveRecipe(i));
            dotsContainer.appendChild(dot);
        }
        
        // 네비게이션 버튼 생성
        createCarouselNavigation(carousel);
        
        updateCarousel();
    }

    /**
     * 캐러셀 네비게이션 버튼 생성
     * @param {HTMLElement} carousel - 캐러셀 컨테이너
     */
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

    /**
     * 활성 레시피 설정
     * @param {number} index - 레시피 인덱스
     */
    function setActiveRecipe(index) {
        if (index < 0 || index >= carouselDisplayCount) return;
        activeRecipeIndex = index;
        updateCarousel();
    }

    /**
     * 캐러셀 업데이트
     */
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
            
            // 카드 배경색 업데이트 (하얀색 계열)
            const cardElement = card.querySelector('.carousel-card');
            if (cardElement) {
                // 하얀색 계열로 변경 (밝기 조정만)
                const brightness = 100 - absOffset * 10;
                cardElement.style.backgroundColor = `hsl(0deg, 0%, ${Math.max(brightness, 90)}%)`;
            }
            
            // 텍스트 투명도 업데이트
            const h3 = card.querySelector('h3');
            const recipeImage = card.querySelector('.recipe-image');
            const recipeInfo = card.querySelector('.recipe-info');
            if (h3) h3.style.opacity = isActive;
            if (recipeImage) recipeImage.style.opacity = isActive;
            if (recipeInfo) recipeInfo.style.opacity = isActive;
        });
        
        // 도트 업데이트
        dots.forEach((dot, i) => {
            dot.classList.toggle('active', i === activeRecipeIndex);
        });
        
        // 네비게이션 버튼 표시/숨김
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
            const card = document.createElement('div');
            card.className = 'recipe-card';
            card.style.cursor = 'pointer';
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
            
            card.addEventListener('click', (e) => {
                if (!e.target.closest('.favorite-btn')) {
                    window.location.href = '/recipes/' + recipe.id + '/cooking/';
                }
            });
            
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
     * @param {number} recipeId - 레시피 ID
     * @param {HTMLElement} button - 버튼 요소
     */
    function toggleFavorite(recipeId, button) {
        button.classList.toggle('active');
        // TODO: 서버에 찜하기 상태 업데이트 요청
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
                // fallback: data-attribute 방식
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

        // 유통기한 임박한 순으로 정렬 (ingredients.js의 sortIngredients 로직 참고)
        ingredients.sort((a, b) => {
            // daysLeft 값을 숫자로 변환하여 비교
            const getDaysValue = (daysLeft) => {
                // null, undefined, 빈 문자열, '-' 처리
                if (!daysLeft || daysLeft === '-' || daysLeft === null || daysLeft === undefined) return null;
                if (daysLeft === 'D-Day') return 0;
                if (typeof daysLeft === 'string' && daysLeft.startsWith('D+')) {
                    // 지난 것 (D+3 → -3)
                    return -parseInt(daysLeft.substring(2)) || null;
                }
                if (typeof daysLeft === 'string' && daysLeft.startsWith('D-')) {
                    // 남은 일수 (D-5 → 5)
                    return parseInt(daysLeft.substring(2)) || null;
                }
                return null;
            };
            
            const daysA = getDaysValue(a.daysLeft);
            const daysB = getDaysValue(b.daysLeft);
            
            // 1. 소비기한 비교 (없는 것은 맨 뒤로)
            if (daysA !== null && daysB === null) return -1; // A는 있고 B는 없음 -> A가 앞
            if (daysA === null && daysB !== null) return 1;  // A는 없고 B는 있음 -> B가 앞
            
            if (daysA !== null && daysB !== null) {
                if (daysA < daysB) return -1; // 날짜 빠른 순 (임박순)
                if (daysA > daysB) return 1;
            }
            
            // 2. 날짜가 같거나 둘 다 없으면 -> 이름 가나다순
            const nameA = a.name || '';
            const nameB = b.name || '';
            return nameA.localeCompare(nameB, 'ko');
        });

        // 8개까지만 표시
        //ingredients = ingredients.slice(0, 8);

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
     * 홈 검색 → 레시피 검색 탭 이동
     */
    function initSearchNavigation() {
        const searchIconBtn = document.getElementById('searchIconBtn');
        const searchInput = document.getElementById('searchInput');
        const searchBar = document.querySelector('.search-bar');

        function goToRecipeSearch(keyword) {
            const url = keyword && keyword.trim()
                ? '/recipes/?q=' + encodeURIComponent(keyword.trim())
                : '/recipes/';
            window.location.href = url;
        }

        if (searchIconBtn) {
            searchIconBtn.addEventListener('click', () => goToRecipeSearch());
        }
        if (searchBar) {
            searchBar.addEventListener('click', (e) => {
                if (e.target === searchInput) return; // input 클릭 시 포커스만 (Enter로 이동)
                goToRecipeSearch(searchInput ? searchInput.value : '');
            });
        }
        if (searchInput) {
            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    goToRecipeSearch(searchInput.value);
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
            // TODO: 레시피 추가 페이지로 이동
            console.log('레시피 추가 기능');
        });
    }

    /**
     * HTML 이스케이프
     * @param {string} text - 이스케이프할 텍스트
     * @returns {string} 이스케이프된 텍스트
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 레시피 데이터 설정 (서버에서 받은 데이터)
     * @param {Array} recipeData - 레시피 데이터 배열
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
            // 헤더의 실제 높이를 계산하여 컨테이너 패딩 설정
            const headerHeight = header.offsetHeight;
            appContainer.style.paddingTop = headerHeight + 'px';
        }
    }

    // DOM 로드 완료 시 초기화
    document.addEventListener('DOMContentLoaded', () => {
        // 서버에서 받은 레시피 데이터 설정
        const recipeDataElement = document.getElementById('recipeData');
        if (recipeDataElement) {
            const recipeData = JSON.parse(recipeDataElement.textContent);
            setRecipes(recipeData);
        }

        initCarousel();
        initFavoriteRecipes();
        initIngredients();
        initDiarySlider();
        initSearchNavigation();
        initFloatingButton();
        
        // 헤더 높이에 맞춰 컨테이너 패딩 조정
        adjustContainerPadding();
        
        // 리사이즈 시에도 패딩 조정
        window.addEventListener('resize', adjustContainerPadding);
        
        // 스크롤 헤더 축소 초기화 (다른 초기화 이후에 실행)
        setTimeout(function() {
            var mainHeader = document.getElementById('mainHeader');
            var searchIconBtn = document.getElementById('searchIconBtn');
            
            if (!mainHeader) {
                console.error('mainHeader를 찾을 수 없습니다');
                return;
            }
            
            console.log('✅ 헤더 스크롤 이벤트 초기화 완료');
            console.log('현재 스크롤 위치:', window.pageYOffset || window.scrollY || 0);
            
            // 스크롤 이벤트 리스너 추가
            var scrollHandler = function(e) {
                toggleHeaderOnScroll();
            };
            
            // window 스크롤 이벤트
            window.addEventListener('scroll', scrollHandler, { passive: true });
            
            // document 스크롤 이벤트도 추가
            document.addEventListener('scroll', scrollHandler, { passive: true });
            
            // documentElement와 body에도 추가
            document.documentElement.addEventListener('scroll', scrollHandler, { passive: true });
            document.body.addEventListener('scroll', scrollHandler, { passive: true });
            
            console.log('✅ 스크롤 이벤트 리스너 추가됨 (window, document, documentElement, body)');
            
            // 초기 상태 설정
            mainHeader.classList.remove('scrolled');
            isScrolled = false;
            // CSS로 처리되므로 display 조작 불필요
            
            // 초기 스크롤 상태 확인
            toggleHeaderOnScroll();
            
            // 테스트: 스크롤 이벤트가 발생하는지 확인
            var scrollTestCount = 0;
            var originalToggle = toggleHeaderOnScroll;
            window.testScroll = function() {
                scrollTestCount++;
                var y = window.pageYOffset || window.scrollY || 0;
                console.log('스크롤 이벤트 발생 #' + scrollTestCount + ', 위치:', y);
                originalToggle();
            };
            
            // 테스트용: 수동으로 스크롤 시뮬레이션 함수
            window.testHeaderScroll = function() {
                console.log('테스트: 헤더 상태 강제 변경');
                mainHeader.classList.toggle('scrolled');
                console.log('헤더에 scrolled 클래스 있음?', mainHeader.classList.contains('scrolled'));
            };
            
            console.log('💡 테스트: 콘솔에서 testHeaderScroll() 실행하면 헤더 상태 변경 확인 가능');
        }, 100);
    });

    // 전역으로 내보내기 (필요한 경우)
    window.MainPage = {
        setRecipes: setRecipes,
        setActiveRecipe: setActiveRecipe,
        toggleHeaderOnScroll: toggleHeaderOnScroll
    };

})();
