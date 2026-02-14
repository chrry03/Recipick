/**
 * static/js/recipes_list.js
 * 찜 기능 + 내 재료만 필터 (완전 수정)
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
        },
        handleUnauthorized: () => {
            alert('로그인이 만료되었습니다. 다시 로그인해주세요.');
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            window.location.href = '/users/login/?next=' + encodeURIComponent(window.location.pathname);
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
        
        const displayTitle = recipe.title_ko || recipe.display_title || recipe.title || '레시피';
        
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
        } else {
            ownedText = "정보 없음";
            missingText = "정보 없음";
        }

        return `
            <div class="recipe-list-card" data-id="${recipe.recipe_id}">
                <div class="card-header-row">
                    <h3 class="card-title">${RecipeUtils.escapeHtml(displayTitle)}</h3>
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
        
        if (!token) {
            return;
        }

        try {
            const response = await fetch('/recipes/api/favorites/', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.status === 401) {
                RecipeUtils.handleUnauthorized();
                return;
            }

            if (response.ok) {
                const favorites = await response.json();
                
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
                
                updateStarIcons();
            }
        } catch (error) {
            console.error('찜 목록 로드 실패:', error);
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
            return;
        }
        
        const token = RecipeUtils.getAccessToken();
        const csrfToken = RecipeUtils.getCsrfToken();
        
        if (!token) {
            alert('로그인이 필요합니다');
            window.location.href = '/users/login/';
            return;
        }

        currentState.processingIds.add(recipeId);

        try {
            const response = await fetch('/recipes/api/favorites/toggle/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ recipe_id: recipeId })
            });
            
            if (response.status === 401) {
                RecipeUtils.handleUnauthorized();
                return;
            }
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.is_favorite) {
                    currentState.favoritedIds.add(recipeId);
                    btn.classList.remove('inactive');
                    btn.classList.add('active');
                } else {
                    currentState.favoritedIds.delete(recipeId);
                    btn.classList.remove('active');
                    btn.classList.add('inactive');
                    
                    if (currentState.filter === 'favorites') {
                        const card = btn.closest('.recipe-list-card');
                        if (card) {
                            card.remove();
                            updateCount(document.querySelectorAll('.recipe-list-card').length);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('❌ 찜 처리 오류:', error);
            alert('찜 처리 중 오류가 발생했습니다');
        } finally {
            currentState.processingIds.delete(recipeId);
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
            
            // ========== [핵심] 내 재료만 필터 ==========
            const onlyOwnedIngredients = (currentState.filter === 'my-ingredients');
            
            console.log('========================================');
            console.log('🔍 [JS] 현재 필터:', currentState.filter);
            console.log('🔒 [JS] 내 재료만:', onlyOwnedIngredients);
            console.log('========================================');
            
            const payload = {
                ingredient_ids: [],
                use_all: true,
                include_spoonacular: true,
                max_results: 500,
                keyword: keyword,
                only_owned_ingredients: onlyOwnedIngredients
            };
            
            console.log('📤 [JS] 요청 페이로드:', JSON.stringify(payload, null, 2));

            const token = RecipeUtils.getAccessToken();
            const headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': RecipeUtils.getCsrfToken()
            };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const res = await fetch(url, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const errorText = await res.text();
                console.error('❌ [JS] API 에러:', res.status, errorText);
                throw new Error(`API Error: ${res.status}`);
            }
            
            const data = await res.json();
            
            console.log('📥 [JS] 응답 데이터:', data);
            console.log('📊 [JS] total_count:', data.total_count);

            let recipeList = [];
            if (data.recipes && Array.isArray(data.recipes)) {
                recipeList = data.recipes;
                console.log('✅ [JS] recipes 필드 사용:', recipeList.length, '개');
            } else if (data.categories) {
                if(data.categories.urgent_ready && data.categories.urgent_ready.recipes) {
                    recipeList.push(...data.categories.urgent_ready.recipes);
                }
                if(data.categories.ready && data.categories.ready.recipes) {
                    recipeList.push(...data.categories.ready.recipes);
                }
                if(data.categories.almost_ready && data.categories.almost_ready.recipes) {
                    recipeList.push(...data.categories.almost_ready.recipes);
                }
                console.log('✅ [JS] categories 필드 사용:', recipeList.length, '개');
            }
            
            console.log('✅ [JS] 최종 레시피:', recipeList.length, '개');
            console.log('========================================');

            renderToDOM(recipeList, keyword);

        } catch (err) {
            console.error('❌ [JS] 레시피 로드 오류:', err);
            DOM.container.innerHTML = getEmptyHTML('레시피를 불러오지 못했습니다.');
        } finally {
            DOM.spinner.classList.remove('show');
            currentState.isLoading = false;
        }
    }

    async function displayFavorites() {
        const token = RecipeUtils.getAccessToken();
        
        if (!token) {
            DOM.container.innerHTML = getEmptyHTML('로그인이 필요합니다');
            DOM.spinner.classList.remove('show');
            currentState.isLoading = false;
            return;
        }

        try {
            const response = await fetch('/recipes/api/favorites/', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.status === 401) {
                RecipeUtils.handleUnauthorized();
                return;
            }

            if (!response.ok) {
                throw new Error('찜 목록 로드 실패');
            }
            
            const data = await response.json();
            
            let favoritesList = [];
            
            if (Array.isArray(data)) {
                favoritesList = data;
            } else if (data && typeof data === 'object' && Array.isArray(data.results)) {
                favoritesList = data.results;
            }
            
            if (favoritesList.length === 0) {
                DOM.container.innerHTML = getEmptyHTML('찜한 레시피가 없습니다');
                DOM.spinner.classList.remove('show');
                currentState.isLoading = false;
                return;
            }
            
            let recipeList = favoritesList.map(item => {
                if (item.recipe && typeof item.recipe === 'object') {
                    const recipe = item.recipe;
                    if (item.ingredients_status) {
                        recipe.ingredients_status = item.ingredients_status;
                    }
                    return recipe;
                }
                return item;
            }).filter(r => r && r.recipe_id);
            
            renderToDOM(recipeList, '');
            
        } catch (error) {
            console.error('찜 목록 로드 오류:', error);
            DOM.container.innerHTML = getEmptyHTML('찜한 레시피를 불러오지 못했습니다');
        } finally {
            DOM.spinner.classList.remove('show');
            currentState.isLoading = false;
        }
    }

    function renderToDOM(list, keyword) {
        console.log('🎨 [JS] renderToDOM 시작:', list.length, '개');
        
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
        attachClickEvents();
        updateStarIcons();
        
        console.log('🎨 [JS] 렌더링 완료:', list.length, '개');
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

    // === 6. 초기화 ===
    document.addEventListener('DOMContentLoaded', async () => {
        console.log('🚀 [JS] 페이지 로드 시작');
        
        await loadFavoriteStatus();
        
        const urlParams = new URLSearchParams(window.location.search);
        const filterParam = urlParams.get('filter');
        const searchKeyword = (urlParams.get('q') || '').trim();
        const focusSearch = urlParams.get('focus') === 'search';

        if (filterParam) {
            const targetChip = Array.from(DOM.filterChips).find(
                chip => chip.dataset.filter === filterParam
            );
            
            if (targetChip) {
                DOM.filterChips.forEach(c => c.classList.remove('active'));
                targetChip.classList.add('active');
                currentState.filter = filterParam;
                console.log('🎯 [JS] URL에서 필터 설정:', filterParam);
            }
        }

        if (searchKeyword && DOM.searchInput) {
            DOM.searchInput.value = searchKeyword;
            await fetchAndRenderRecipes('search', searchKeyword);
        } else {
            await fetchAndRenderRecipes();
        }

        if (DOM.searchInput) {
            DOM.searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    fetchAndRenderRecipes('search', DOM.searchInput.value);
                }
            });
            if (focusSearch) {
                DOM.searchInput.focus();
            }
        }

        DOM.filterChips.forEach(chip => {
            chip.addEventListener('click', () => {
                console.log('🔘 [JS] 필터 클릭:', chip.dataset.filter);
                DOM.filterChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                currentState.filter = chip.dataset.filter;
                console.log('🔘 [JS] 필터 변경됨:', currentState.filter);
                fetchAndRenderRecipes('recommend');
            });
        });
        
        console.log('✅ [JS] 초기화 완료');
    });

})();