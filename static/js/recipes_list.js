/**
 * static/js/recipes_list.js
 * 찜 기능 완전 해결 + URL 파라미터 처리
 */

(function() {
    'use strict';

    // === 1. 유틸리티 ===
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
        getAccessToken: () => {
            const token = localStorage.getItem('access_token');
            if (token) return token;
            return RecipeUtils.getCookie('access_token');
        },
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
        filter: 'all',
        isLoading: false,
        favoritedIds: new Set(),
        processingIds: new Set()
    };

    // === 3. 레시피 카드 HTML 생성 ===
    function buildRecipeCardHTML(recipe) {
        const diffMap = { 'EASY': '쉬움', 'NORMAL': '보통', 'DIFFICULT': '어려움' };
        const difficulty = diffMap[recipe.difficulty] || '보통';
        const isLiked = currentState.favoritedIds.has(recipe.recipe_id);
        
        let ownedText = "없음";
        let missingText = "없음";

        if (recipe.ingredients_status && recipe.ingredients_status.ingredients_status) {
            const statusMap = recipe.ingredients_status.ingredients_status;
            let owned = [];
            let missing = [];

            for (const [name, status] of Object.entries(statusMap)) {
                if (['has_expired', 'has_urgent'].includes(name)) continue;
                
                if (typeof status === 'object' && status !== null) {
                    if (status.is_owned) {
                        owned.push(name);
                    } else {
                        missing.push(name);
                    }
                } else {
                    if (status === 'missing') {
                        missing.push(name);
                    } else {
                        owned.push(name);
                    }
                }
            }
            if (owned.length > 0) ownedText = owned.join(', ');
            if (missing.length > 0) missingText = missing.join(', ');
        }

        return `
            <div class="recipe-list-card" data-id="${recipe.recipe_id}">
                <div class="card-header-row">
                    <h3 class="card-title">${RecipeUtils.escapeHtml(recipe.title)}</h3>
                    <button class="card-like-btn ${isLiked ? 'active' : 'inactive'}" 
                            data-recipe-id="${recipe.recipe_id}"
                            onclick="event.stopPropagation();">
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

    // === 4. 찜 기능 ===
    async function loadFavoriteStatus() {
        const token = RecipeUtils.getAccessToken();
        console.log('🔑 [loadFavoriteStatus] 토큰:', token ? '있음' : '없음');
        
        if (!token) {
            console.log('⚠️ [loadFavoriteStatus] 비로그인');
            return;
        }

        try {
            console.log('📡 [loadFavoriteStatus] GET /recipes/api/favorites/');
            
            const response = await fetch('/recipes/api/favorites/', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            console.log('📥 [loadFavoriteStatus] 응답:', response.status);

            if (response.ok) {
                const favorites = await response.json();
                console.log('✅ [loadFavoriteStatus] 찜 목록:', favorites);
                
                currentState.favoritedIds.clear();
                
                if (Array.isArray(favorites)) {
                    favorites.forEach(fav => {
                        if (fav.recipe && fav.recipe.recipe_id) {
                            currentState.favoritedIds.add(fav.recipe.recipe_id);
                        } else if (fav.recipe_id) {
                            currentState.favoritedIds.add(fav.recipe_id);
                        }
                    });
                }
                
                console.log('💛 [loadFavoriteStatus] 찜한 ID:', Array.from(currentState.favoritedIds));
                updateStarIcons();
            } else {
                const errorText = await response.text();
                console.error('❌ [loadFavoriteStatus] 실패:', response.status, errorText);
            }
        } catch (error) {
            console.error('❌ [loadFavoriteStatus] 오류:', error);
        }
    }

    function updateStarIcons() {
        document.querySelectorAll('.card-like-btn').forEach(btn => {
            const recipeId = parseInt(btn.dataset.recipeId);
            
            if (currentState.processingIds.has(recipeId)) {
                return;
            }
            
            if (currentState.favoritedIds.has(recipeId)) {
                btn.classList.remove('inactive');
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
                btn.classList.add('inactive');
            }
        });
    }

    async function handleFavoriteClick(btn) {
        const recipeId = parseInt(btn.dataset.recipeId);
        
        if (currentState.processingIds.has(recipeId)) {
            console.log('⏳ 이미 처리 중:', recipeId);
            return;
        }
        
        const isLiked = currentState.favoritedIds.has(recipeId);
        
        console.log('⭐ 별 클릭:', recipeId, isLiked ? '찜 취소' : '찜 추가');

        const token = RecipeUtils.getAccessToken();
        const csrfToken = RecipeUtils.getCsrfToken();
        
        if (!token) {
            alert('로그인이 필요합니다');
            window.location.href = '/users/login/';
            return;
        }

        currentState.processingIds.add(recipeId);
        btn.classList.add('processing');
        btn.disabled = true;

        try {
            if (isLiked) {
                console.log('📡 찜 취소 요청:', recipeId);
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
                    currentState.favoritedIds.delete(recipeId);
                    btn.classList.remove('active');
                    btn.classList.add('inactive');
                    console.log('✅ 찜 취소 성공');
                    
                    // ========== [추가] 찜한 레시피 탭에서 삭제 시 카드 제거 ==========
                    if (currentState.filter === 'favorites') {
                        const card = btn.closest('.recipe-list-card');
                        if (card) {
                            card.remove();
                            updateCount(document.querySelectorAll('.recipe-list-card').length);
                        }
                    }
                } else {
                    throw new Error(`찜 취소 실패: ${response.status}`);
                }
            } else {
                console.log('📡 찜 추가 요청:', recipeId);
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
                    currentState.favoritedIds.add(recipeId);
                    btn.classList.remove('inactive');
                    btn.classList.add('active');
                    console.log('✅ 찜 추가 성공');
                } else {
                    throw new Error(`찜 추가 실패: ${response.status}`);
                }
            }
        } catch (error) {
            console.error('❌ 찜 처리 오류:', error);
            alert('찜 처리 중 오류가 발생했습니다');
        } finally {
            currentState.processingIds.delete(recipeId);
            btn.classList.remove('processing');
            btn.disabled = false;
        }
    }

    // === 5. 데이터 로드 및 렌더링 ===
    async function fetchAndRenderRecipes(mode = 'recommend', keyword = '') {
        if (!DOM.container) return;
        
        currentState.isLoading = true;
        DOM.spinner.classList.add('show');
        DOM.container.innerHTML = '';

        try {
            if (currentState.filter === 'favorites' && mode !== 'search') {
                await displayFavorites();
                return;
            }

            const url = '/recipes/api/recommendations/';
            const payload = {
                ingredient_ids: [],
                use_all: true,
                include_spoonacular: true,
                max_results: 500,
                keyword: keyword
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

            let recipeList = [];
            if (data.recipes) {
                recipeList = data.recipes;
            } else if (data.categories) {
                if(data.categories.urgent_ready) recipeList.push(...data.categories.urgent_ready.recipes);
                if(data.categories.ready) recipeList.push(...data.categories.ready.recipes);
                if(data.categories.almost_ready) recipeList.push(...data.categories.almost_ready.recipes);
            }

            console.log('✅ 최종 레시피:', recipeList.length, '개');
            renderToDOM(recipeList, keyword);

        } catch (err) {
            console.error('❌ 레시피 로드 오류:', err);
            DOM.container.innerHTML = getEmptyHTML('레시피를 불러오지 못했습니다.');
        } finally {
            DOM.spinner.classList.remove('show');
            currentState.isLoading = false;
        }
    }

    /**
     * ========== [완전 수정] 찜한 레시피 표시 ==========
     */
    async function displayFavorites() {
        const token = RecipeUtils.getAccessToken();
        
        console.log('========================================');
        console.log('📡 [displayFavorites] 시작');
        console.log('========================================');
        
        if (!token) {
            console.log('⚠️ 비로그인');
            DOM.container.innerHTML = getEmptyHTML('로그인이 필요합니다');
            DOM.spinner.classList.remove('show');
            currentState.isLoading = false;
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

            console.log('📥 응답:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ 응답 실패:', response.status, errorText);
                throw new Error(`찜 목록 로드 실패: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('✅ 응답 데이터:', data);
            console.log('📊 타입:', Array.isArray(data) ? '배열' : typeof data);
            console.log('📊 길이:', Array.isArray(data) ? data.length : 'N/A');
            
            if (Array.isArray(data)) {
                if (data.length === 0) {
                    console.log('ℹ️ 찜한 레시피 0개');
                    DOM.container.innerHTML = getEmptyHTML('찜한 레시피가 없습니다');
                    DOM.spinner.classList.remove('show');
                    currentState.isLoading = false;
                    return;
                }
                
                console.log('🔄 레시피 추출 시작');
                
                // ========== [핵심] recipe 추출 ==========
                let recipeList = data.map((item, index) => {
                    if (item.recipe && typeof item.recipe === 'object') {
                        return item.recipe;
                    }
                    if (item.recipe_id || item.title) {
                        return item;
                    }
                    return null;
                }).filter(r => r && (r.recipe_id || r.id));
                
                console.log('📦 추출 완료:', recipeList.length, '개');
                
                if (recipeList.length === 0) {
                    console.error('❌ 레시피 추출 실패');
                    DOM.container.innerHTML = getEmptyHTML('찜한 레시피 데이터를 처리할 수 없습니다');
                    DOM.spinner.classList.remove('show');
                    currentState.isLoading = false;
                    return;
                }
                
                // ========== [추가] recipe_id 정규화 ==========
                recipeList = recipeList.map(recipe => {
                    if (!recipe.recipe_id && recipe.id) {
                        recipe.recipe_id = recipe.id;
                    }
                    return recipe;
                });
                
                console.log('🎨 렌더링 시작:', recipeList.length, '개');
                renderToDOM(recipeList, '');
                console.log('========================================');
            } else {
                console.error('❌ 잘못된 응답 형식:', data);
                throw new Error('응답 형식 오류');
            }
            
        } catch (error) {
            console.error('========================================');
            console.error('❌ displayFavorites 오류:', error);
            console.error('========================================');
            DOM.container.innerHTML = getEmptyHTML('찜한 레시피를 불러오지 못했습니다');
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

        console.log('🎨 렌더링:', list.length, '개');

        let html = '<div class="recipe-card-grid">';
        list.forEach(item => {
            html += buildRecipeCardHTML(item);
        });
        html += '</div>';
        
        DOM.container.innerHTML = html;
        
        updateCount(list.length);
        attachClickEvents();
    }

    function attachClickEvents() {
        const cards = document.querySelectorAll('.recipe-list-card');
        cards.forEach(card => {
            card.addEventListener('click', () => {
                const id = card.dataset.id;
                window.location.href = `/recipes/${id}/cooking/`;
            });
        });

        const likeButtons = document.querySelectorAll('.card-like-btn');
        likeButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                handleFavoriteClick(btn);
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
        const activeChip = document.querySelector('.filter-chip.active');
        if (activeChip) {
            const text = activeChip.textContent.trim();
            const baseName = text.replace(/\(\d+\)/, '').trim();
            activeChip.textContent = `${baseName}(${num})`;
        }
    }

    // ========== [추가] 탭 카운트 업데이트 함수 ==========
    function updateTabCount(filter, count) {
        const chip = Array.from(DOM.filterChips).find(
            c => c.dataset.filter === filter
        );
        if (chip) {
            const countSpan = chip.querySelector('.count');
            if (countSpan) {
                countSpan.textContent = `(${count})`;
                console.log(`📊 ${filter} 카운트 업데이트: ${count}`);
            }
        }
    }

    // ========== [추가] 내 재료만 카운트 계산 ==========
    async function updateMyIngredientsCount() {
        const token = RecipeUtils.getAccessToken();
        if (!token) {
            updateTabCount('my-ingredients', 0);
            return;
        }

        try {
            const response = await fetch('/recipes/api/recommendations/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'X-CSRFToken': RecipeUtils.getCsrfToken()
                },
                body: JSON.stringify({
                    ingredient_ids: [],
                    use_all: true,
                    include_spoonacular: true,
                    max_results: 500,
                    only_owned_ingredients: true
                })
            });

            if (response.ok) {
                const data = await response.json();
                const count = data.total_count || 0;
                updateTabCount('my-ingredients', count);
                console.log('🥘 내 재료만 카운트:', count);
            }
        } catch (error) {
            console.error('❌ 내 재료만 카운트 실패:', error);
            updateTabCount('my-ingredients', 0);
        }
    }

    // === 6. 초기화 ===
    document.addEventListener('DOMContentLoaded', async () => {
        console.log('🚀 [DOMContentLoaded] 초기화 시작');
        
        await loadFavoriteStatus();
        console.log('✅ 찜 상태 로드 완료:', Array.from(currentState.favoritedIds));
        
        // ========== [추가] 찜한 레시피 카운트 즉시 업데이트 ==========
        updateTabCount('favorites', currentState.favoritedIds.size);
        
        // ========== [추가] URL 파라미터로 필터 확인 ==========
        const urlParams = new URLSearchParams(window.location.search);
        const filterParam = urlParams.get('filter');
        const searchKeyword = (urlParams.get('q') || '').trim();
        
        console.log('🔍 URL 파라미터:', { filter: filterParam, q: searchKeyword });

        // ========== [추가] filter 파라미터가 있으면 해당 필터 활성화 ==========
        if (filterParam) {
            const targetChip = Array.from(DOM.filterChips).find(
                chip => chip.dataset.filter === filterParam
            );
            
            if (targetChip) {
                console.log('🎯 필터 자동 선택:', filterParam);
                DOM.filterChips.forEach(c => c.classList.remove('active'));
                targetChip.classList.add('active');
                currentState.filter = filterParam;
            }
        }

        if (searchKeyword && DOM.searchInput) {
            DOM.searchInput.value = searchKeyword;
            fetchAndRenderRecipes('search', searchKeyword);
        } else {
            fetchAndRenderRecipes();
        }
        
        // ========== [추가] 초기 로드 후 내 재료만 카운트 계산 ==========
        await updateMyIngredientsCount();

        if (DOM.searchInput) {
            DOM.searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    fetchAndRenderRecipes('search', DOM.searchInput.value);
                }
            });
        }

        DOM.filterChips.forEach(chip => {
            chip.addEventListener('click', () => {
                console.log('🔘 필터 클릭:', chip.dataset.filter);
                DOM.filterChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                currentState.filter = chip.dataset.filter;
                fetchAndRenderRecipes('recommend');
            });
        });
        
        console.log('✅ 초기화 완료');
    });

})();