/**
 * static/js/recipes_list.js
 * 레시피 목록 전용 스크립트 (요리 모드 로직 제외)
 */

(function() {
    'use strict';

    // === 1. 유틸리티 (중복 방지용 내부 함수) ===
    const RecipeUtils = {
        getCookie: (name) => {
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
        },
        getCsrfToken: () => RecipeUtils.getCookie('csrftoken'),
        escapeHtml: (text) => {
            if (!text) return '';
            return text.replace(/[&<>"']/g, function(m) {
                return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
            });
        }
    };

    // === 2. DOM 요소 참조 ===
    const DOM = {
        container: document.getElementById('recipe-recommendations'),
        searchInput: document.getElementById('recipe-search-input'),
        spinner: document.getElementById('loading-spinner'),
        filterChips: document.querySelectorAll('.filter-chip')
    };

    // 현재 상태 관리
    let currentState = {
        filter: 'all', // all, favorites, my-ingredients
        isLoading: false
    };

    // === 3. 핵심 기능: 레시피 카드 HTML 생성 (Figma 스타일) ===
    function buildRecipeCardHTML(recipe) {
        // 데이터 가공
        const diffMap = { 'EASY': '쉬움', 'NORMAL': '보통', 'DIFFICULT': '어려움' };
        const difficulty = diffMap[recipe.difficulty] || '보통';
        const isLiked = recipe.is_favorited ? true : false;
        
        // 재료 텍스트 분리 (보유 vs 미보유)
        let ownedText = "-";
        let missingText = "없음";

        if (recipe.ingredients_status && recipe.ingredients_status.ingredients_status) {
            const statusMap = recipe.ingredients_status.ingredients_status;
            let owned = [];
            let missing = [];

            for (const [name, status] of Object.entries(statusMap)) {
                if (['has_expired', 'has_urgent'].includes(name)) continue;
                if (status === 'missing') missing.push(name);
                else owned.push(name);
            }
            if (owned.length > 0) ownedText = owned.join(', ');
            if (missing.length > 0) missingText = missing.join(', ');
        }

        // HTML 조립
        return `
            <div class="recipe-list-card" data-id="${recipe.recipe_id}">
                <div class="card-header-row">
                    <h3 class="card-title">${RecipeUtils.escapeHtml(recipe.title)}</h3>
                    <button class="card-like-btn ${isLiked ? 'active' : 'inactive'}" 
                            onclick="event.stopPropagation(); window.handleRecipeLike(${recipe.recipe_id}, this)">
                        ★
                    </button>
                </div>

                <div class="card-image-wrap">
                    <img src="${recipe.image_url || '/static/images/default-recipe.jpg'}" 
                         class="card-img" 
                         loading="lazy"
                         onerror="this.src='/static/images/default-recipe.jpg'">
                </div>

                <div class="card-info-box">
                    <div class="info-item-row">
                        <span class="info-key">조리시간</span>
                        <span class="info-val">${recipe.ready_minutes}분</span>
                    </div>
                    <div class="info-item-row">
                        <span class="info-key">난이도</span>
                        <span class="info-val">${difficulty}</span>
                    </div>
                    <div class="info-item-row">
                        <span class="info-key">보유 재료</span>
                        <span class="info-val">${ownedText}</span>
                    </div>
                    <div class="info-item-row">
                        <span class="info-key">없는 재료</span>
                        <span class="info-val val-missing">${missingText}</span>
                    </div>
                </div>
            </div>
        `;
    }

    // === 4. 데이터 로드 및 렌더링 ===
    async function fetchAndRenderRecipes(mode = 'recommend', keyword = '') {
        if (!DOM.container) return;
        
        currentState.isLoading = true;
        DOM.spinner.classList.add('show');
        DOM.container.innerHTML = '';

        try {
            // 필터가 '찜한 레시피'인 경우 별도 처리 (API가 준비되었다면 호출)
            if (currentState.filter === 'favorites' && mode !== 'search') {
                // TODO: 찜한 목록 API 호출로 변경 가능
                DOM.container.innerHTML = getEmptyHTML('찜한 레시피가 없습니다.');
                return;
            }

            // API 호출 준비
            const url = '/recipes/api/recommendations/';
            const payload = {
                ingredient_ids: [],
                use_all: true,
                include_spoonacular: true,
                max_results: 20,
                keyword: keyword // 검색어
            };

            const res = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': RecipeUtils.getCsrfToken()
                },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error('API Error');
            const data = await res.json();

            // 결과 데이터 통합 (카테고리 구조 -> 단일 리스트)
            let recipeList = [];
            if (data.recipes) {
                recipeList = data.recipes;
            } else if (data.categories) {
                // 순서: 임박 -> 가능 -> 부족
                if(data.categories.urgent_ready) recipeList.push(...data.categories.urgent_ready.recipes);
                if(data.categories.ready) recipeList.push(...data.categories.ready.recipes);
                if(data.categories.almost_ready) recipeList.push(...data.categories.almost_ready.recipes);
            }

            renderToDOM(recipeList, keyword);

        } catch (err) {
            console.error(err);
            DOM.container.innerHTML = getEmptyHTML('레시피를 불러오지 못했습니다.');
        } finally {
            DOM.spinner.classList.remove('show');
            currentState.isLoading = false;
        }
    }

    function renderToDOM(list, keyword) {
        if (!list || list.length === 0) {
            const msg = keyword ? `'${keyword}' 검색 결과가 없습니다.` : '추천 레시피가 없습니다.';
            DOM.container.innerHTML = getEmptyHTML(msg);
            updateCount(0);
            return;
        }

        let html = '<div class="recipe-card-grid">';
        list.forEach(item => {
            html += buildRecipeCardHTML(item);
        });
        html += '</div>';
        
        DOM.container.innerHTML = html;
        updateCount(list.length);
        
        // 클릭 이벤트 연결 (쿠킹 모드 이동)
        attachClickEvents();
    }

    function attachClickEvents() {
        const cards = document.querySelectorAll('.recipe-list-card');
        cards.forEach(card => {
            card.addEventListener('click', () => {
                const id = card.dataset.id;
                // [요청사항] 상세페이지 건너뛰고 바로 요리 모드로!
                window.location.href = `/recipes/${id}/cooking/`;
            });
        });
    }

    function getEmptyHTML(msg) {
        return `
            <div class="list-empty-state">
                <img src="/static/images/empty_fridge.png">
                <p>${msg}</p>
            </div>
        `;
    }

    function updateCount(num) {
        const activeChip = document.querySelector('.filter-chip.active .count');
        if (activeChip) activeChip.textContent = `(${num})`;
    }

    // === 5. 외부 노출 함수 (찜하기) ===
    window.handleRecipeLike = async function(id, btn) {
        if (!id) return;
        
        // 낙관적 UI 업데이트 (즉시 반응)
        const isLiked = btn.classList.contains('active');
        if (isLiked) {
            btn.classList.remove('active');
            btn.classList.add('inactive');
        } else {
            btn.classList.remove('inactive');
            btn.classList.add('active');
        }

        try {
            // 실제 서버 요청
            await fetch(`/recipes/api/recipes/${id}/favorite/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': RecipeUtils.getCsrfToken()
                }
            });
        } catch (e) {
            console.error(e);
            // 실패 시 원복
            if (isLiked) btn.classList.add('active');
            else btn.classList.remove('active');
            alert('오류가 발생했습니다.');
        }
    };

    // === 6. 초기화 및 이벤트 리스너 ===
    document.addEventListener('DOMContentLoaded', () => {
        // 초기 로드
        fetchAndRenderRecipes();

        // 검색 엔터키
        if (DOM.searchInput) {
            DOM.searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    fetchAndRenderRecipes('search', DOM.searchInput.value);
                }
            });
        }

        // 필터 칩 클릭
        DOM.filterChips.forEach(chip => {
            chip.addEventListener('click', () => {
                DOM.filterChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                currentState.filter = chip.dataset.filter;
                fetchAndRenderRecipes('recommend'); // 필터 변경 시 다시 로드
            });
        });
    });

})();