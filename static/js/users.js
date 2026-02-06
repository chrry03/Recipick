/* static/js/users.js - 최종 수정본 (API 연동 포함) */

// ==========================================
// 1. 전역 유틸리티 함수 & 데이터
// ==========================================

// CSRF 토큰 가져오기
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

// 알러지 데이터 (고정)
const ALLERGIES_DATA = [
    "난류", "우유", "메밀", "땅콩", "대두", "밀", "고등어", "게", "새우", "돼지고기", 
    "복숭아", "토마토", "아황산류", "호두", "닭고기", "쇠고기", "오징어", "조개류", "잣"
];

// 식재료 데이터 관리 변수
let currentCategoryId = 1; 
const selectedAllergies = new Set();
const bannedIngredients = new Set(); 


// ==========================================
// 2. 전역 함수 (렌더링 및 로직)
// ==========================================

// 2-1. 알러지 렌더링 (고정 데이터 사용)
function renderAllergies() {
    const container = document.getElementById('allergy-list');
    if(!container) return;
    
    container.innerHTML = ALLERGIES_DATA.map(name => `
        <div class="allergy-item" onclick="toggleAllergy(this, '${name}')">
            <div class="allergy-img-box">
                <img src="/static/images/ingredients/${name}.png" onerror="this.style.display='none'; this.parentNode.innerText='${name[0]}'">
            </div>
            <div class="allergy-name">${name}</div>
        </div>
    `).join('');
}

function toggleAllergy(el, name) {
    el.classList.toggle('selected');
    if (selectedAllergies.has(name)) selectedAllergies.delete(name);
    else selectedAllergies.add(name);
}

// 2-2. [신규] 카테고리 API 호출 및 렌더링
async function fetchCategories() {
    const container = document.getElementById('category-wrapper');
    if (!container) return;

    try {
        const res = await fetch('/ingredients/categories/'); 
        const categories = await res.json();
        
        container.innerHTML = categories.map((cat, index) => `
            <div class="category-item ${index === 0 ? 'active' : ''}" 
                 onclick="selectCategory(this, ${cat.id})">
                ${cat.icon_url || ''} ${cat.name}
            </div>
        `).join('');

        if (categories.length > 0) {
            currentCategoryId = categories[0].id;
            fetchIngredients(currentCategoryId);
        }
    } catch (err) {
        console.error("카테고리 로드 실패:", err);
    }
}

// 2-3. [신규] 카테고리 선택
function selectCategory(el, catId) {
    document.querySelectorAll('.category-item').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    currentCategoryId = catId;
    fetchIngredients(catId);
}

// 2-4. [신규] 식재료 목록 API 호출
async function fetchIngredients(catId) {
    const container = document.getElementById('ingredient-list');
    if (!container) return;
    container.innerHTML = '<div style="padding:20px; width:100%; text-align:center;">로딩 중...</div>';

    try {
        const res = await fetch(`/ingredients/?category_id=${catId}`);
        const ingredients = await res.json();
        renderIngredientList(ingredients);
    } catch (err) {
        console.error("식재료 로드 실패:", err);
        container.innerHTML = '<div style="padding:20px;">불러오기 실패</div>';
    }
}

// 2-5. [신규] 검색 기능
async function searchIngredients(keyword) {
    if (!keyword.trim()) return;
    
    const container = document.getElementById('ingredient-list');
    container.innerHTML = '<div style="padding:20px; width:100%; text-align:center;">검색 중...</div>';

    try {
        const res = await fetch(`/ingredients/search/?keyword=${keyword}`);
        const ingredients = await res.json();

        if (ingredients.length > 0) {
            renderIngredientList(ingredients);
        } else {
            container.innerHTML = `
                <div class="no-result" style="text-align:center; padding:20px; width:100%;">
                    <p style="margin-bottom:10px; color:#666;">'${keyword}'에 대한 검색 결과가 없습니다.</p>
                    <button type="button" class="btn-mw btn-primary-mw" 
                            onclick="addCustomIngredient('${keyword}')" style="width:auto; padding: 10px 20px;">
                        '${keyword}' 직접 추가하기
                    </button>
                </div>
            `;
        }
    } catch (err) {
        console.error("검색 실패:", err);
    }
}

// 2-6. [신규] 리스트 렌더링 (공통)
function renderIngredientList(list) {
    const container = document.getElementById('ingredient-list');
    container.innerHTML = list.map(ing => {
        const isChecked = bannedIngredients.has(ing.name_ko) ? 'checked' : '';
        return `
            <label class="ing-check-item">
                <input type="checkbox" value="${ing.name_ko}" class="ing-checkbox" onchange="updateBanned(this)" ${isChecked}>
                <span>${ing.name_ko}</span>
            </label>
        `;
    }).join('');
}

// 2-7. [신규] 직접 추가
function addCustomIngredient(name) {
    bannedIngredients.add(name);
    alert(`'${name}'이(가) 제외 식재료에 추가되었습니다.`);
    
    const container = document.getElementById('ingredient-list');
    const newItem = `
        <label class="ing-check-item">
            <input type="checkbox" value="${name}" class="ing-checkbox" onchange="updateBanned(this)" checked>
            <span>${name} (직접 추가)</span>
        </label>
    `;
    if(container.querySelector('.no-result')) container.innerHTML = ''; 
    container.insertAdjacentHTML('afterbegin', newItem);
}

// 2-8. 체크박스 상태 업데이트
function updateBanned(checkbox) {
    if (checkbox.checked) bannedIngredients.add(checkbox.value);
    else bannedIngredients.delete(checkbox.value);
}

// 2-9. 전체 선택/해제
function toggleSelectAll() {
    const checkboxes = document.querySelectorAll('.ing-checkbox');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    checkboxes.forEach(cb => {
        cb.checked = !allChecked;
        updateBanned(cb);
    });
}

// 2-10. 단계 이동
function goToStep(stepNum) {
    document.querySelectorAll('.step-section').forEach(el => el.classList.remove('active'));
    document.getElementById(`step-${stepNum}`).classList.add('active');
}

// 2-11. 설정 완료 및 저장 (Flat 구조)
async function finishPreference(level) {
    const token = localStorage.getItem('access_token');
    const csrftoken = getCookie('csrftoken');

    if (!token) {
        alert("로그인이 필요합니다.");
        window.location.href = '/users/login/';
        return;
    }
    
    const payload = {
        cooking_level: level,
        allergies: Array.from(selectedAllergies),
        banned_ingredients: Array.from(bannedIngredients)
    };

    try {
        const response = await fetch('/users/mypage/', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            alert("취향 설정이 완료되었습니다! 메인으로 이동합니다.");
            window.location.href = "/"; 
        } else {
            const errorData = await response.json();
            console.error("저장 실패:", errorData);
            alert("저장에 실패했습니다. 다시 시도해주세요.");
        }
    } catch (error) {
        console.error("통신 오류:", error);
        alert("서버 오류가 발생했습니다.");
    }
}


// ==========================================
// 3. DOMContentLoaded 이벤트
// ==========================================
document.addEventListener('DOMContentLoaded', function() {

    // --- [수정됨] 취향 설정 페이지 초기화 ---
    const allergyContainer = document.getElementById('allergy-list');
    if (allergyContainer) {
        renderAllergies();
        fetchCategories(); // ★ API 카테고리 로드

        // ★ 검색창 엔터키 이벤트 연결
        const searchInput = document.getElementById('ingredient-search');
        if (searchInput) {
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    searchIngredients(this.value);
                }
            });
        }
    }

    // --- 1. 로그인 폼 ---
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault(); 
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const csrftoken = getCookie('csrftoken');

            try {
                const response = await fetch('/users/login/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify({ login_type: 'email', email: email, password: password })
                });
                const data = await response.json();
                if (response.ok) {
                    localStorage.setItem('access_token', data.token.access);
                    localStorage.setItem('refresh_token', data.token.refresh);
                    localStorage.setItem('user_nickname', data.user.nickname);
                    window.location.href = '/';
                } else {
                    alert(data.message || '로그인 실패');
                }
            } catch (error) {
                console.error(error);
                alert('서버 통신 오류: 서버 상태를 확인해주세요.');
            }
        });
    }

    // --- 2. 회원가입 폼 (Step 1) ---
    const signupForm = document.getElementById('signup-step1-form');
    if (signupForm) {
        signupForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const passwordConfirm = document.getElementById('password_confirm').value;

            if (password !== passwordConfirm) {
                alert('비밀번호가 일치하지 않습니다.');
                return;
            }

            try {
                const response = await fetch('/users/check-email/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email })
                });
                
                const data = await response.json();

                if (!data.is_available) {
                    alert(data.message);
                    return; 
                }

                localStorage.setItem('temp_email', email);
                localStorage.setItem('temp_pw', password);
                window.location.href = '/users/nickname/?next=preference';

            } catch (error) {
                console.error('이메일 확인 중 오류:', error);
                alert('서버 오류가 발생했습니다.');
            }
        });
    }

    // --- 3. 닉네임 설정 폼 ---
    const nicknameForm = document.getElementById('nickname-form');
    if (nicknameForm) {
        nicknameForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const nickname = document.getElementById('nickname').value;
            const csrftoken = getCookie('csrftoken');
            if (!nickname) return alert('닉네임을 입력해주세요.');

            try {
                const checkRes = await fetch(`/users/check-nickname/?nickname=${nickname}`);
                const checkData = await checkRes.json();
                if (!checkRes.ok || !checkData.is_available) {
                    return alert('이미 사용 중인 닉네임입니다.');
                }

                const tempEmail = localStorage.getItem('temp_email');
                const tempPw = localStorage.getItem('temp_pw');
                const urlParams = new URLSearchParams(window.location.search);
                const nextStep = urlParams.get('next');

                if (tempEmail && tempPw) {
                    // 신규 가입
                    const signupRes = await fetch('/users/signup/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                        body: JSON.stringify({ email: tempEmail, password: tempPw, nickname: nickname })
                    });
                    const signupData = await signupRes.json();
                    if (signupRes.status === 201) {
                        alert('가입 완료!');
                        localStorage.removeItem('temp_email');
                        localStorage.removeItem('temp_pw');
                        
                        if (signupData.token) {
                            localStorage.setItem('access_token', signupData.token.access);
                            localStorage.setItem('refresh_token', signupData.token.refresh);
                        }
                        localStorage.setItem('user_nickname', nickname);
                        
                        if(nextStep === 'preference') window.location.href = '/users/preference/';
                        else window.location.href = '/';
                    } else {
                        alert(signupData.message || '가입 실패');
                    }
                } else {
                    // 닉네임 변경 (토큰 사용)
                    const token = localStorage.getItem('access_token');
                    if(token) {
                        const updateRes = await fetch('/users/mypage/', {
                            method: 'PATCH',
                            headers: { 
                                'Content-Type': 'application/json',
                                'Authorization': `Bearer ${token}`,
                                'X-CSRFToken': csrftoken
                            },
                            body: JSON.stringify({ nickname: nickname })
                        });
                        if(updateRes.ok) {
                            alert('변경 완료');
                            localStorage.setItem('user_nickname', nickname);
                            window.location.href = '/users/mypage/';
                        }
                    } else {
                        alert("로그인 정보가 없습니다.");
                        window.location.href = '/users/login/';
                    }
                }
            } catch (e) {
                console.error(e);
                alert('오류 발생');
            }
        });
    }

    // --- 4. 마이페이지 로직 ---
    const loggedInView = document.getElementById('logged-in-view');
    if (loggedInView) {
        const token = localStorage.getItem('access_token');
        const loggedOutView = document.getElementById('logged-out-view');
        const nicknameDisplay = document.getElementById('display-nickname');

        if (token) {
            loggedInView.style.display = 'flex';
            if (loggedOutView) loggedOutView.style.display = 'none';
            if(nicknameDisplay) nicknameDisplay.textContent = localStorage.getItem('user_nickname') || '사용자';
        } else {
            loggedInView.style.display = 'none';
            if (loggedOutView) loggedOutView.style.display = 'flex';
        }

        const logoutBtn = document.getElementById('btn-logout');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', async function() {
                if (confirm('로그아웃 하시겠습니까?')) {
                    try {
                        const refresh = localStorage.getItem('refresh_token');
                        const csrftoken = getCookie('csrftoken');

                        await fetch('/users/logout/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': csrftoken,
                                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                            },
                            body: JSON.stringify({ refresh: refresh })
                        });

                    } catch (error) {
                        console.error("로그아웃 요청 중 오류:", error);
                    } finally {
                        localStorage.removeItem('access_token');
                        localStorage.removeItem('refresh_token');
                        localStorage.removeItem('user_nickname');
                        alert("로그아웃 되었습니다.");
                        window.location.href = '/users/login/';
                    }
                }
            });
        }
    }
});