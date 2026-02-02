/**
 * 레시피 추천 API 호출
 * 
 * @param {Array} ingredientIds - 선택한 식재료 ID 배열 (선택사항)
 * @param {Boolean} useAll - 모든 식재료 사용 여부 (기본: true)
 * @param {Boolean} includeSpoonacular - Spoonacular API 사용 여부 (기본: true)
 * @param {Number} maxResults - 최대 결과 개수 (기본: 20)
 * @returns {Promise} API 응답 데이터
 */
async function getRecipeRecommendations(ingredientIds = [], useAll = true, includeSpoonacular = true, maxResults = 20) {
    // JWT 토큰 가져오기
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
                // 토큰 만료 시 리프레시 시도
                const refreshed = await refreshAccessToken();
                if (refreshed) {
                    // 재시도
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
 * 
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
 * 레시피 추천 결과 렌더링
 * 
 * @param {Object} data - API 응답 데이터
 */
function renderRecipeRecommendations(data) {
    const container = document.getElementById('recipe-recommendations');
    
    if (!container) {
        console.error('recipe-recommendations 컨테이너를 찾을 수 없습니다');
        return;
    }
    
    // 결과가 없는 경우
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
    
    // 카테고리별로 렌더링
    const categories = data.categories;
    
    // 1. 긴급 (유통기한 임박)
    if (categories.urgent_ready && categories.urgent_ready.count > 0) {
        html += renderCategorySection(
            '🔥 ' + categories.urgent_ready.label,
            categories.urgent_ready.recipes,
            'urgent'
        );
    }
    
    // 2. 바로 가능
    if (categories.ready && categories.ready.count > 0) {
        html += renderCategorySection(
            '✨ ' + categories.ready.label,
            categories.ready.recipes,
            'ready'
        );
    }
    
    // 3. 재료 1-2개 부족
    if (categories.almost_ready && categories.almost_ready.count > 0) {
        html += renderCategorySection(
            '👍 ' + categories.almost_ready.label,
            categories.almost_ready.recipes,
            'almost'
        );
    }
    
    container.innerHTML = html;
}

/**
 * 카테고리 섹션 렌더링
 * 
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
 * 레시피 카드 HTML 생성
 * 
 * @param {Object} recipe - 레시피 데이터
 * @returns {String} HTML 문자열
 */
function createRecipeCard(recipe) {
    // difficulty는 enum 값 ('EASY', 'NORMAL', 'DIFFICULT')
    const difficultyMap = {
        'EASY': '쉬움',
        'NORMAL': '보통',
        'DIFFICULT': '어려움'
    };
    const difficultyText = difficultyMap[recipe.difficulty] || '보통';
    
    const score = recipe.recommendation_score || {};
    const totalScore = score.total_score || 0;
    const missingCount = score.missing_ingredients_count || 0;
    
    // 이미지 URL (없으면 기본 이미지)
    const imageUrl = recipe.image_url || '/static/images/default-recipe.jpg';
    
    // 점수에 따른 뱃지 색상
    let scoreClass = '';
    if (totalScore >= 90) {
        scoreClass = 'score-urgent';
    } else if (totalScore >= 75) {
        scoreClass = 'score-ready';
    } else {
        scoreClass = 'score-almost';
    }
    
    return `
        <div class="recipe-card" onclick="location.href='/recipes/${recipe.recipe_id}/'">
            <img src="${imageUrl}" 
                 alt="${recipe.title}" 
                 class="recipe-image"
                 onerror="this.src='/static/images/default-recipe.jpg'">
            <div class="recipe-info">
                <div class="recipe-name">${recipe.title}</div>
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
 * Access Token 가져오기 (localStorage 또는 cookie)
 * 
 * @returns {String|null} Access Token
 */
function getAccessToken() {
    // localStorage에서 가져오기 (JWT 방식)
    const token = localStorage.getItem('access_token');
    
    if (token) {
        return token;
    }
    
    // Cookie에서 가져오기 (세션 방식)
    const cookieToken = getCookie('access_token');
    if (cookieToken) {
        return cookieToken;
    }
    
    return null;
}

/**
 * Access Token 갱신
 * 
 * @returns {Boolean} 갱신 성공 여부
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
        
        // 새 토큰 저장
        localStorage.setItem('access_token', data.access);
        
        console.log('Access token 갱신 성공');
        return true;
        
    } catch (error) {
        console.error('토큰 갱신 오류:', error);
        
        // 갱신 실패 시 로그인 페이지로 리다이렉트
        alert('로그인이 만료되었습니다. 다시 로그인해주세요.');
        window.location.href = '/users/login/';
        
        return false;
    }
}

/**
 * Cookie 값 가져오기
 * 
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
 * CSRF Token 가져오기 (Django CSRF 보호용)
 * 
 * @returns {String|null} CSRF Token
 */
function getCSRFToken() {
    return getCookie('csrftoken');
}

// 전역으로 함수 노출 (다른 파일에서 사용 가능)
window.getRecipeRecommendations = getRecipeRecommendations;
window.searchRecipes = searchRecipes;
window.renderRecipeRecommendations = renderRecipeRecommendations;