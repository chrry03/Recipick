/**
 * 일지 관련 JavaScript
 */

(function() {
    'use strict';

    // 일지 작성 페이지 초기화
    if (document.getElementById('log-create-form')) {
        initLogCreate();
    }

    // 일지 목록 페이지 초기화
    if (document.getElementById('recipeList')) {
        initLogList();
    }

    /**
     * 일지 작성 페이지 초기화
     */
    function initLogCreate() {
        const elements = {
            form: document.getElementById('log-create-form'),
            imageUpload: document.getElementById('imageUpload'),
            imageInput: document.getElementById('imageInput'),
            imagePreview: document.getElementById('imagePreview'),
            difficultyStars: document.getElementById('difficultyStars'),
            satisfactionStars: document.getElementById('satisfactionStars'),
            difficultyRating: document.getElementById('difficultyRating'),
            satisfactionRating: document.getElementById('satisfactionRating'),
            memoInput: document.getElementById('memoInput'),
            cookedAt: document.getElementById('cookedAt'),
            submitBtn: document.getElementById('submitBtn'),
            recipeName: document.getElementById('recipeName')
        };

        const state = {
            difficultyRating: 0,
            satisfactionRating: 0
        };

        if (elements.imageUpload && elements.imageInput) {
            elements.imageUpload.addEventListener('click', () => {
                elements.imageInput.click();
            });

            elements.imageInput.addEventListener('change', (e) => {
                handleImageSelect(e, elements);
            });
        }

        if (elements.difficultyStars) {
            initRatingGroup(elements.difficultyStars, 'difficulty', state, elements);
        }
        if (elements.satisfactionStars) {
            initRatingGroup(elements.satisfactionStars, 'satisfaction', state, elements);
        }

        if (elements.cookedAt) {
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            elements.cookedAt.value = `${year}-${month}-${day}`;
        }

        if (elements.form) {
            elements.form.addEventListener('submit', (e) => {
                handleFormSubmit(e, state, elements);
            });
        }
    }

    /**
     * 이미지 선택 처리
     */
    function handleImageSelect(e, elements) {
        const file = e.target.files[0];
        if (!file) return;

        if (file.size > 10 * 1024 * 1024) {
            alert('파일 크기는 10MB 이하여야 합니다.');
            return;
        }

        if (!file.type.startsWith('image/')) {
            alert('이미지 파일만 업로드 가능합니다.');
            return;
        }

        const reader = new FileReader();
        reader.onload = (event) => {
            elements.imagePreview.src = event.target.result;
            elements.imagePreview.style.display = 'block';
            elements.imageUpload.classList.add('has-image');
            elements.imageUpload.style.display = 'none';
        };
        reader.onerror = () => {
            alert('이미지를 불러오는 중 오류가 발생했습니다.');
        };
        reader.readAsDataURL(file);
    }

    /**
     * 별점 그룹 초기화
     */
    function initRatingGroup(container, type, state, elements) {
        const starButtons = container.querySelectorAll('.star-btn');
        const hiddenInput = type === 'difficulty' ? elements.difficultyRating : elements.satisfactionRating;

        starButtons.forEach((btn, index) => {
            btn.addEventListener('click', () => {
                const rating = index + 1;
                updateStars(starButtons, rating);
                
                if (type === 'difficulty') {
                    state.difficultyRating = rating;
                    if (hiddenInput) hiddenInput.value = rating;
                } else {
                    state.satisfactionRating = rating;
                    if (hiddenInput) hiddenInput.value = rating;
                }
            });
        });
    }

    /**
     * 별점 업데이트
     */
    function updateStars(starButtons, rating) {
        starButtons.forEach((btn, index) => {
            if (index < rating) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    /**
     * 폼 제출 처리
     */
    async function handleFormSubmit(e, state, elements) {
        e.preventDefault();

        if (state.difficultyRating === 0) {
            alert('난이도를 선택해주세요.');
            return;
        }

        if (state.satisfactionRating === 0) {
            alert('만족도를 선택해주세요.');
            return;
        }

        if (elements.submitBtn) {
            elements.submitBtn.disabled = true;
            elements.submitBtn.textContent = '저장 중...';
        }

        try {
            const formData = new FormData(elements.form);
            console.log('일지 저장 데이터:', {
                recipe_name: elements.recipeName?.textContent || '',
                difficulty_rating: state.difficultyRating,
                satisfaction_rating: state.satisfactionRating,
                memo: elements.memoInput?.value || '',
                cooked_at: elements.cookedAt?.value || '',
                image: elements.imageInput?.files[0] ? '파일 업로드됨' : '없음'
            });

            // TODO: 실제 API 호출
            alert('일지가 작성되었습니다!');
        } catch (error) {
            console.error('일지 저장 오류:', error);
            alert('일지 저장 중 오류가 발생했습니다.');
        } finally {
            if (elements.submitBtn) {
                elements.submitBtn.disabled = false;
                elements.submitBtn.textContent = '작성하기';
            }
        }
    }

    /**
     * 일지 목록 페이지 초기화
     */
    function initLogList() {
        const prevBtn = document.getElementById('prevMonth');
        const nextBtn = document.getElementById('nextMonth');
        const currentMonthEl = document.getElementById('currentMonth');
        const recipeItems = document.querySelectorAll('.recipe-item');
        const instagramShareBtn = document.getElementById('instagramShareBtn');

        // 현재 월 파싱 (예: "2월" -> 2)
        let currentMonth = 1;
        if (currentMonthEl) {
            const monthText = currentMonthEl.textContent.trim();
            const monthMatch = monthText.match(/(\d+)/);
            if (monthMatch) {
                currentMonth = parseInt(monthMatch[1]);
            } else {
                currentMonth = new Date().getMonth() + 1;
            }
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', (e) => {
                e.preventDefault();
                currentMonth = currentMonth === 1 ? 12 : currentMonth - 1;
                updateMonth(currentMonth, currentMonthEl);
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                currentMonth = currentMonth === 12 ? 1 : currentMonth + 1;
                updateMonth(currentMonth, currentMonthEl);
            });
        }

        recipeItems.forEach((item) => {
            item.addEventListener('click', () => {
                const logId = item.dataset.logId;
                if (logId) {
                    // TODO: 상세 페이지로 이동
                    console.log('일지 상세 페이지로 이동:', logId);
                }
            });
        });

        // 인스타그램 공유 버튼 이벤트
        if (instagramShareBtn) {
            instagramShareBtn.addEventListener('click', handleInstagramShare);
        }
    }

    /**
     * 인스타그램 공유 처리
     */
    function handleInstagramShare() {
        // 현재 페이지 URL 또는 선택한 일지 정보를 인스타그램으로 공유
        const currentUrl = window.location.href;
        const shareText = 'Recipick에서 요리 일지를 확인해보세요!';
        
        // 인스타그램 스토리 공유 URL 생성
        // 참고: 인스타그램은 직접 공유 API가 없어서 클립보드에 복사하거나 안내 메시지를 표시
        if (navigator.share) {
            navigator.share({
                title: 'Recipick 요리 일지',
                text: shareText,
                url: currentUrl
            }).catch((error) => {
                console.log('공유 실패:', error);
                // 클립보드에 복사
                copyToClipboard(currentUrl);
            });
        } else {
            // 클립보드에 복사
            copyToClipboard(currentUrl);
            alert('링크가 클립보드에 복사되었습니다. 인스타그램에서 공유해주세요!');
        }
    }

    /**
     * 클립보드에 텍스트 복사
     */
    function copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                console.log('클립보드에 복사됨:', text);
            });
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.opacity = '0';
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
        }
    }

    /**
     * 월 업데이트
     */
    function updateMonth(month, element) {
        if (element) {
            element.textContent = `${month}월`;
        }
        
        // URL 파라미터 업데이트 (페이지 새로고침 없이)
        const url = new URL(window.location);
        url.searchParams.set('month', month);
        window.history.pushState({ month: month }, '', url);
        
        // TODO: AJAX로 해당 월의 데이터 로드
        console.log(`${month}월 데이터 로드`);
        
        // 실제로는 여기서 AJAX 요청을 보내서 해당 월의 일지 데이터를 가져와야 합니다
        // loadLogsForMonth(month);
    }

})();


// 일지 디테일
// 뒤로가기 기능
function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/journal/';
    }
}

// 새 일지 추가 기능
function addNewJournal() {
    window.location.href = '/journal/create/';
}

// 알림 버튼 클릭
document.querySelector('.notification-btn')?.addEventListener('click', function() {
    // 알림 페이지로 이동 또는 알림 모달 표시
    window.location.href = '/notifications/';
});

// 더보기 버튼 클릭 (수정/삭제 메뉴)
document.querySelector('.more-btn')?.addEventListener('click', function() {
    const menu = document.createElement('div');
    menu.className = 'context-menu';
    menu.innerHTML = `
        <div class="menu-overlay"></div>
        <div class="menu-content">
            <button class="menu-item" onclick="editJournal()">수정하기</button>
            <button class="menu-item delete" onclick="deleteJournal()">삭제하기</button>
            <button class="menu-item cancel" onclick="closeMenu()">취소</button>
        </div>
    `;
    document.body.appendChild(menu);
    
    // 메뉴 스타일 추가
    const style = document.createElement('style');
    style.textContent = `
        .context-menu {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1000;
        }
        .menu-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
        }
        .menu-content {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            background: white;
            border-radius: 20px 20px 0 0;
            padding: 20px;
            animation: slideUp 0.3s ease;
        }
        @keyframes slideUp {
            from {
                transform: translateY(100%);
            }
            to {
                transform: translateY(0);
            }
        }
        .menu-item {
            width: 100%;
            padding: 16px;
            border: none;
            background: none;
            font-size: 16px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
            text-align: center;
            font-family: 'Noto Sans KR', sans-serif;
        }
        .menu-item:last-child {
            border-bottom: none;
        }
        .menu-item.delete {
            color: #ff4444;
        }
        .menu-item.cancel {
            font-weight: 500;
        }
        .menu-item:hover {
            background: #f5f5f5;
        }
    `;
    document.head.appendChild(style);
    
    // 오버레이 클릭시 메뉴 닫기
    menu.querySelector('.menu-overlay').addEventListener('click', closeMenu);
});

// 메뉴 닫기
function closeMenu() {
    const menu = document.querySelector('.context-menu');
    if (menu) {
        menu.style.animation = 'slideDown 0.3s ease';
        setTimeout(() => menu.remove(), 300);
    }
}

// 일지 수정
function editJournal() {
    closeMenu();
    const journalId = getJournalIdFromURL();
    window.location.href = `/journal/edit/${journalId}/`;
}

// 일지 삭제
function deleteJournal() {
    if (confirm('정말 이 일지를 삭제하시겠습니까?')) {
        const journalId = getJournalIdFromURL();
        // CSRF 토큰 가져오기
        const csrfToken = getCookie('csrftoken');
        
        fetch(`/journal/delete/${journalId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => {
            if (response.ok) {
                alert('일지가 삭제되었습니다.');
                window.location.href = '/journal/';
            } else {
                alert('삭제에 실패했습니다.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('오류가 발생했습니다.');
        });
    }
    closeMenu();
}

// URL에서 일지 ID 추출
function getJournalIdFromURL() {
    const path = window.location.pathname;
    const match = path.match(/\/journal\/(\d+)\//);
    return match ? match[1] : null;
}

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

// 네비게이션 활성화 상태 관리
function setActiveNav() {
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (currentPath.includes(href)) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

// 페이지 로드시 실행
document.addEventListener('DOMContentLoaded', function() {
    setActiveNav();
    
    // 이미지 로드 실패시 기본 이미지 표시
    const recipeImage = document.querySelector('.recipe-image img');
    if (recipeImage) {
        recipeImage.addEventListener('error', function() {
            this.src = '/static/images/default-recipe.jpg';
        });
    }
    
    // 뒤로가기 버튼 이벤트
    document.querySelector('.back-btn')?.addEventListener('click', goBack);
    
    // FAB 버튼 이벤트
    document.querySelector('.fab')?.addEventListener('click', addNewJournal);
});

// 스크롤시 헤더 그림자 효과
let lastScroll = 0;
window.addEventListener('scroll', function() {
    const header = document.querySelector('.header');
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > 50) {
        header.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
    } else {
        header.style.boxShadow = 'none';
    }
    
    lastScroll = currentScroll;
});

// 터치 제스처 지원 (스와이프로 뒤로가기)
let touchStartX = 0;
let touchEndX = 0;

document.addEventListener('touchstart', function(event) {
    touchStartX = event.changedTouches[0].screenX;
}, false);

document.addEventListener('touchend', function(event) {
    touchEndX = event.changedTouches[0].screenX;
    handleSwipe();
}, false);

function handleSwipe() {
    // 왼쪽에서 오른쪽으로 스와이프 (뒤로가기)
    if (touchEndX > touchStartX + 50 && touchStartX < 50) {
        goBack();
    }
}

