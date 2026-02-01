// 알림 페이지
document.addEventListener('DOMContentLoaded', function() {
    // 뒤로가기 버튼 이벤트
    const backButton = document.querySelector('.back-button');
    if (backButton) {
        backButton.addEventListener('click', function() {
            // Django에서 뒤로가기 처리
            window.history.back();
        });
    }

    // 더보기 버튼 이벤트 (모든 버튼에 적용)
    const moreButtons = document.querySelectorAll('.more-button');
    moreButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            showOptionsMenu(e, this);
        });
    });

    // 알림 아이템 클릭 이벤트
    const notificationItem = document.querySelector('.notification-item-container');
    if (notificationItem) {
        notificationItem.addEventListener('click', function() {
            // 알림 상세 페이지로 이동
            console.log('알림 클릭됨');
            // window.location.href = '/notification-detail/';
        });
    }
});

// 옵션 메뉴 표시 함수
function showOptionsMenu(event, buttonElement) {
    // 기존 메뉴가 있으면 제거
    const existingMenu = document.querySelector('.options-menu');
    if (existingMenu) {
        existingMenu.remove();
        return;
    }

    // 버튼이 속한 알림 아이템 컨테이너 찾기
    const notificationItem = buttonElement.closest('.notification-item-container');
    if (!notificationItem) return;

    // 새 메뉴 생성
    const menu = document.createElement('div');
    menu.className = 'options-menu';
    const notificationId = buttonElement.getAttribute('data-notification-id');
    menu.setAttribute('data-notification-id', notificationId);
    menu.innerHTML = `
        <div class="option-item" onclick="markAsRead(${notificationId})">읽음으로 표시</div>
        <div class="option-item" onclick="deleteNotification(${notificationId})">삭제</div>
    `;

    // 메뉴를 알림 아이템 컨테이너 내부에 추가 (relative positioning을 위해)
    notificationItem.appendChild(menu);

    // 위치 계산 (버튼 바로 아래)
    const buttonRect = buttonElement.getBoundingClientRect();
    const itemRect = notificationItem.getBoundingClientRect();
    
    // 버튼의 오른쪽 끝에서 메뉴의 오른쪽 끝까지의 거리
    const rightOffset = itemRect.right - buttonRect.right;

    // 스타일 추가
    menu.style.position = 'absolute';
    menu.style.right = rightOffset + 'px';
    menu.style.top = '100%';
    menu.style.marginTop = '5px';

    // 외부 클릭시 메뉴 닫기
    setTimeout(() => {
        document.addEventListener('click', closeMenu);
    }, 0);
}

// 메뉴 닫기 함수
function closeMenu() {
    const menu = document.querySelector('.options-menu');
    if (menu) {
        menu.remove();
    }
    document.removeEventListener('click', closeMenu);
}

// 알림 삭제 함수
function deleteNotification(notificationId) {
    if (confirm('알림을 삭제하시겠습니까?')) {
        console.log('알림 삭제:', notificationId);
    }
    closeMenu();
}

// 읽음으로 표시 함수
function markAsRead(notificationId) {
    console.log('읽음으로 표시:', notificationId);
    closeMenu();
}

// CSRF 토큰 가져오기 함수
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

