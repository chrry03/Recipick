/**
 * static/js/recipes_list.js
 * 찜한 레시피 탭 완전 해결 버전
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
            console.log('⚠️ [loadFavoriteStatus] 비로그인 상태');
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
                max_results: 500,  // 50 → 500으로 증가
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

            console.log('📦 API 응답:', {
                hasRecipes: !!data.recipes,
                hasCategories: !!data.categories
            });

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
        console.log('🔑 토큰:', token ? '있음 (길이: ' + token.length + ')' : '없음');
        console.log('========================================');
        
        if (!token) {
            console.log('⚠️ [displayFavorites] 비로그인 - 로그인 페이지로 이동 안내');
            DOM.container.innerHTML = getEmptyHTML('로그인이 필요합니다');
            DOM.spinner.classList.remove('show');
            currentState.isLoading = false;
            return;
        }

        try {
            console.log('📡 [displayFavorites] 요청 시작');
            console.log('   URL: /recipes/api/favorites/');
            console.log('   Method: GET');
            console.log('   Headers:', {
                'Authorization': 'Bearer ' + token.substring(0, 10) + '...',
                'Content-Type': 'application/json'
            });
            
            const response = await fetch('/recipes/api/favorites/', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            console.log('📥 [displayFavorites] 응답 수신');
            console.log('   Status:', response.status, response.statusText);
            console.log('   OK:', response.ok);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ [displayFavorites] 응답 실패');
                console.error('   Status:', response.status);
                console.error('   Error:', errorText);
                throw new Error(`찜 목록 로드 실패: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('✅ [displayFavorites] 응답 파싱 성공');
            console.log('   데이터 타입:', Array.isArray(data) ? '배열' : typeof data);
            console.log('   데이터 길이:', Array.isArray(data) ? data.length : 'N/A');
            console.log('   원본 데이터:', data);
            
            if (Array.isArray(data) && data.length > 0) {
                console.log('📊 [displayFavorites] 첫 번째 항목 구조:');
                console.log('   ', data[0]);
                console.log('   Keys:', Object.keys(data[0]));
            }
            
            // ========== [핵심] 데이터 추출 로직 ==========
            let recipeList = [];
            
            if (Array.isArray(data)) {
                if (data.length === 0) {
                    console.log('ℹ️ [displayFavorites] 찜한 레시피 0개');
                    DOM.container.innerHTML = getEmptyHTML('찜한 레시피가 없습니다');
                    DOM.spinner.classList.remove('show');
                    currentState.isLoading = false;
                    return;
                }
                
                console.log('🔄 [displayFavorites] 레시피 추출 시작');
                
                // 각 항목에서 recipe 추출
                recipeList = data.map((item, index) => {
                    console.log(`   [${index}] 처리 중...`);
                    console.log('      구조:', {
                        hasRecipe: !!item.recipe,
                        hasRecipeId: !!item.recipe_id,
                        hasTitle: !!item.title,
                        keys: Object.keys(item)
                    });
                    
                    // recipe 객체가 있으면 그것을 사용
                    if (item.recipe && typeof item.recipe === 'object') {
                        console.log('      → recipe 객체 사용');
                        return item.recipe;
                    }
                    
                    // recipe가 없고 item 자체가 recipe라면
                    if (item.recipe_id || item.title) {
                        console.log('      → item 자체를 recipe로 사용');
                        return item;
                    }
                    
                    console.log('      → null (유효하지 않은 항목)');
                    return null;
                }).filter(r => {
                    const isValid = r && (r.recipe_id || r.id);
                    if (!isValid && r) {
                        console.log('   ⚠️ 필터링됨 (recipe_id/id 없음):', r);
                    }
                    return isValid;
                });
                
                console.log('📦 [displayFavorites] 추출 완료:', recipeList.length, '개');
                
                if (recipeList.length === 0) {
                    console.error('❌ [displayFavorites] 레시피 추출 실패');
                    console.error('   원본 데이터:', data);
                    console.error('   → 모든 항목이 필터링됨');
                    DOM.container.innerHTML = getEmptyHTML('찜한 레시피 데이터를 처리할 수 없습니다');
                    DOM.spinner.classList.remove('show');
                    currentState.isLoading = false;
                    return;
                }
                
                // ========== [추가] recipe_id 정규화 ==========
                console.log('🔄 [displayFavorites] recipe_id 정규화');
                recipeList = recipeList.map(recipe => {
                    if (!recipe.recipe_id && recipe.id) {
                        console.log('   정규화:', recipe.id, '→ recipe_id');
                        recipe.recipe_id = recipe.id;
                    }
                    return recipe;
                });
                
                console.log('🎨 [displayFavorites] 렌더링 시작:', recipeList.length, '개');
                renderToDOM(recipeList, '');
                console.log('========================================');
            } else {
                console.error('❌ [displayFavorites] 잘못된 응답 형식');
                console.error('   예상: 배열, 실제:', typeof data);
                console.error('   데이터:', data);
                throw new Error('응답 형식 오류');
            }
            
        } catch (error) {
            console.error('========================================');
            console.error('❌ [displayFavorites] 최종 오류');
            console.error('   메시지:', error.message);
            console.error('   스택:', error.stack);
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

        console.log('🎨 [renderToDOM] 렌더링 시작:', list.length, '개');

        let html = '<div class="recipe-card-grid">';
        list.forEach(item => {
            html += buildRecipeCardHTML(item);
        });
        html += '</div>';
        
        DOM.container.innerHTML = html;
        
        const renderedCards = document.querySelectorAll('.recipe-list-card');
        console.log('🎯 [renderToDOM] 실제 렌더링:', renderedCards.length, '개');
        
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
            const countSpan = activeChip.querySelector('.count') || activeChip;
            const text = activeChip.textContent.trim();
            const baseName = text.replace(/\(\d+\)/, '').trim();
            activeChip.textContent = `${baseName}(${num})`;
        }
    }

    // === 6. 초기화 ===
    document.addEventListener('DOMContentLoaded', async () => {
        console.log('🚀 [DOMContentLoaded] 초기화 시작');
        
        await loadFavoriteStatus();
        
        const urlParams = new URLSearchParams(window.location.search);
        const searchKeyword = (urlParams.get('q') || '').trim();

        if (searchKeyword && DOM.searchInput) {
            DOM.searchInput.value = searchKeyword;
            requestAnimationFrame(() => {
                fetchAndRenderRecipes('search', searchKeyword);
            });
        } else {
            fetchAndRenderRecipes();
        }

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
        
        console.log('✅ [DOMContentLoaded] 초기화 완료');
    });

})();