/**
 * static/js/recipes_list.js
 * 찜 기능 동기화 + 로딩 충돌 방지 (수정 완료)
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

    // === [🔥 핵심] 상태 관리 및 로딩 제어 ===
    let currentState = {
        filter: 'all',          // 현재 보고 있는 탭 (all, favorites, my-ingredients)
        loadingRequestId: 0,    // 현재 진행 중인 로딩의 고유 ID (Race Condition 방지)
        cache: {                // 간단한 데이터 캐시 (탭 전환 시 깜빡임 방지)
            'all': null,
            'favorites': null,
            'my-ingredients': null
        }
    };

    // === 3. 레시피 카드 HTML 생성 ===
    function buildRecipeCardHTML(recipe) {
        const diffMap = { 'EASY': '쉬움', 'NORMAL': '보통', 'DIFFICULT': '어려움' };
        const difficulty = diffMap[recipe.difficulty] || '보통';
        
        // [🔥 핵심] 서버에서 온 is_favorited 값 사용 (없으면 false)
        const isLiked = recipe.is_favorited === true;
        
        const displayTitle = recipe.title_ko || recipe.display_title || recipe.title || '레시피';
        
        let ownedText = "정보 없음";
        let missingText = "정보 없음";

        // 재료 정보 파싱 (기존 로직 유지)
        if (recipe.ingredients_status && recipe.ingredients_status.ingredients_status) {
            const statusMap = recipe.ingredients_status.ingredients_status;
            let owned = [];
            let missing = [];

            for (const [name, status] of Object.entries(statusMap)) {
                if (['has_expired', 'has_urgent'].includes(name)) continue;
                
                if (typeof status === 'object' && status !== null) {
                    if (status.is_owned) owned.push(name);
                    else missing.push(name);
                } else {
                    if (status === 'missing') missing.push(name);
                    else owned.push(name);
                }
            }
            if (owned.length > 0) ownedText = owned.join(', ');
            if (missing.length > 0) missingText = missing.join(', ');
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

    // === 4. 데이터 로드 및 렌더링 ===
    
    // [🔥 핵심] 로딩 함수: requestId를 사용하여 덮어쓰기 방지
    async function loadRecipes(type, query = '') {
        // 1. 새로운 로딩 시작 시 ID 증가 (이전 요청 무효화)
        const myRequestId = ++currentState.loadingRequestId;
        
        DOM.spinner.classList.add('show');
        DOM.container.innerHTML = ''; // 기존 내용 지우기

        // 2. 캐시 확인 (검색어가 없을 때만)
        if (!query && currentState.cache[currentState.filter]) {
            console.log(`🚀 [JS] 캐시 사용: ${currentState.filter}`);
            renderToDOM(currentState.cache[currentState.filter], '');
            DOM.spinner.classList.remove('show');
            return;
        }

        try {
            let data;
            
            // (A) 찜한 레시피 탭일 경우 (별도 API 호출)
            if (currentState.filter === 'favorites' && type !== 'search') {
                await loadFavoritesData(myRequestId);
                return; // loadFavoritesData 내부에서 처리하고 종료
            } 
            
            // (B) 전체/내재료 탭 + 검색일 경우 (추천 API 호출)
            else {
                // 내 재료만 필터 여부
                const onlyOwned = (currentState.filter === 'my-ingredients');
                
                const payload = {
                    ingredient_ids: [],
                    use_all: true,
                    include_spoonacular: true, // 9초 로딩의 원인 (필요시 false로 변경 고려)
                    max_results: 50,
                    keyword: query,
                    only_owned_ingredients: onlyOwned
                };

                const token = RecipeUtils.getAccessToken();
                const headers = {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': RecipeUtils.getCsrfToken()
                };
                if (token) headers['Authorization'] = `Bearer ${token}`;

                const res = await fetch('/recipes/api/recommendations/', { 
                    method: 'POST', 
                    headers: headers, 
                    body: JSON.stringify(payload) 
                });

                if (!res.ok) throw new Error(`API Error: ${res.status}`);
                data = await res.json();
            }

            // [🔥 핵심] 요청 ID 확인: 내가 보낸 요청이 아니면(더 최신 요청이 있으면) 무시
            if (myRequestId !== currentState.loadingRequestId) {
                console.warn(`🛑 [JS] 오래된 요청(${myRequestId}) 무시됨. (현재: ${currentState.loadingRequestId})`);
                return;
            }

            // 데이터 파싱
            let recipeList = [];
            if (data.recipes) {
                recipeList = data.recipes;
            } else if (data.categories) {
                // 카테고리 구조 평탄화
                if(data.categories.urgent_ready) recipeList.push(...data.categories.urgent_ready.recipes);
                if(data.categories.ready) recipeList.push(...data.categories.ready.recipes);
                if(data.categories.almost_ready) recipeList.push(...data.categories.almost_ready.recipes);
            }

            // 캐시에 저장 (검색어가 없을 때만)
            if (!query) {
                currentState.cache[currentState.filter] = recipeList;
            }

            renderToDOM(recipeList, query);

        } catch (error) {
            console.error('❌ [JS] 로딩 실패:', error);
            if (myRequestId === currentState.loadingRequestId) {
                DOM.container.innerHTML = getEmptyHTML('데이터를 불러오지 못했습니다.');
            }
        } finally {
            if (myRequestId === currentState.loadingRequestId) {
                DOM.spinner.classList.remove('show');
            }
        }
    }

    // 찜 목록 전용 로딩 함수
    async function loadFavoritesData(requestId) {
        const token = RecipeUtils.getAccessToken();
        if (!token) {
            DOM.container.innerHTML = getEmptyHTML('로그인이 필요합니다');
            DOM.spinner.classList.remove('show');
            return;
        }

        try {
            const response = await fetch('/recipes/api/favorites/', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.status === 401) {
                RecipeUtils.handleUnauthorized();
                return;
            }
            
            const data = await response.json();
            
            // [🔥 핵심] 요청 ID 확인
            if (requestId !== currentState.loadingRequestId) return;

            let favoritesList = Array.isArray(data) ? data : (data.results || []);
            
            // 찜 목록 데이터 구조 변환 (Recipe 객체 추출 + ingredients_status 병합 + is_favorited 강제 True)
            let recipeList = favoritesList.map(item => {
                let recipe = item.recipe || item;
                recipe.is_favorited = true; // 찜 목록이니까 당연히 True
                if (item.ingredients_status) {
                    recipe.ingredients_status = item.ingredients_status;
                }
                return recipe;
            });

            currentState.cache['favorites'] = recipeList;
            renderToDOM(recipeList, '');

        } catch (error) {
            console.error(error);
            if (requestId === currentState.loadingRequestId) {
                DOM.container.innerHTML = getEmptyHTML('찜 목록을 불러오지 못했습니다.');
            }
        } finally {
            if (requestId === currentState.loadingRequestId) {
                DOM.spinner.classList.remove('show');
            }
        }
    }

    function renderToDOM(list, keyword) {
        if (!list || list.length === 0) {
            const msg = keyword ? `'${keyword}' 검색 결과가 없습니다.` : '해당하는 레시피가 없습니다.';
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
        
        // 이벤트 리스너 다시 연결
        attachClickEvents();
    }

    function attachClickEvents() {
        // 카드 클릭 (상세 이동)
        document.querySelectorAll('.recipe-list-card').forEach(card => {
            card.addEventListener('click', () => {
                const id = card.dataset.id;
                window.location.href = `/recipes/${id}/cooking/`;
            });
        });

        // 찜 버튼 클릭 (토글)
        document.querySelectorAll('.card-like-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                handleFavoriteClick(btn);
            });
        });
    }

    async function handleFavoriteClick(btn) {
        const recipeId = parseInt(btn.dataset.recipeId);
        const token = RecipeUtils.getAccessToken();
        
        if (!token) {
            alert('로그인이 필요합니다');
            return;
        }

        // UI 즉시 반영 (낙관적 업데이트)
        const isCurrentlyActive = btn.classList.contains('active');
        btn.classList.toggle('active');
        btn.classList.toggle('inactive');

        try {
            const response = await fetch('/recipes/api/favorites/toggle/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'X-CSRFToken': RecipeUtils.getCsrfToken()
                },
                body: JSON.stringify({ recipe_id: recipeId })
            });

            if (!response.ok) throw new Error('Failed');
            
            // 캐시 데이터도 업데이트 (중요!)
            updateCacheFavoriteStatus(recipeId, !isCurrentlyActive);

            // 만약 현재 '찜한 레시피' 탭이고, 찜을 취소했다면 -> 목록에서 제거
            if (currentState.filter === 'favorites' && isCurrentlyActive) {
                const card = btn.closest('.recipe-list-card');
                if (card) {
                    card.remove();
                    // 카운트 업데이트
                    const countSpan = document.querySelector('.filter-chip[data-filter="favorites"] .count');
                    if (countSpan) {
                        const currentCount = parseInt(countSpan.textContent.replace(/\D/g, '')) || 0;
                        countSpan.textContent = `(${Math.max(0, currentCount - 1)})`;
                    }
                }
            }

        } catch (error) {
            // 실패 시 롤백
            console.error(error);
            btn.classList.toggle('active');
            btn.classList.toggle('inactive');
            alert('오류가 발생했습니다.');
        }
    }

    // 캐시된 데이터들의 is_favorited 상태 동기화
    function updateCacheFavoriteStatus(recipeId, isFavorited) {
        Object.keys(currentState.cache).forEach(key => {
            const list = currentState.cache[key];
            if (list) {
                const target = list.find(r => r.recipe_id === recipeId);
                if (target) {
                    target.is_favorited = isFavorited;
                }
                // 찜 탭인 경우, 찜 취소 시 리스트에서 제거 처리 필요 (선택사항)
                if (key === 'favorites' && !isFavorited) {
                    currentState.cache[key] = list.filter(r => r.recipe_id !== recipeId);
                }
            }
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
            activeChip.querySelector('.count').textContent = `(${num})`;
        }
    }

    // === 5. 초기화 ===
    document.addEventListener('DOMContentLoaded', () => {
        // URL 파라미터에서 filter 확인 (예: /recipes/?filter=favorites)
        const urlParams = new URLSearchParams(window.location.search);
        const filterFromUrl = urlParams.get('filter');
        if (filterFromUrl && ['all', 'favorites', 'my-ingredients'].includes(filterFromUrl)) {
            currentState.filter = filterFromUrl;
            DOM.filterChips.forEach(c => c.classList.remove('active'));
            const targetChip = document.querySelector(`.filter-chip[data-filter="${filterFromUrl}"]`);
            if (targetChip) targetChip.classList.add('active');
        }

        // 필터 칩 클릭 이벤트
        DOM.filterChips.forEach(chip => {
            chip.addEventListener('click', () => {
                // 1. 이미 활성화된 탭이면 무시 (불필요한 로딩 방지)
                if (chip.classList.contains('active')) return;

                // 2. UI 변경
                DOM.filterChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                
                // 3. 상태 변경 및 로딩
                currentState.filter = chip.dataset.filter;
                loadRecipes('recommend');
            });
        });

        // 검색 이벤트
        if (DOM.searchInput) {
            DOM.searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const query = DOM.searchInput.value.trim();
                    if (query) {
                        // 검색 시엔 필터를 '전체(all)'로 잠시 간주하거나, 현재 필터 내 검색으로 구현 가능
                        // 여기선 전체 검색으로 처리
                        loadRecipes('search', query);
                    }
                }
            });
        }

        // 초기 로딩 (전체 보기)
        loadRecipes('recommend');
    });

})();