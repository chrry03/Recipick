/**
 * 일지 관련 JavaScript (UI 전용)
 */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        // 1. 공통: 스와이프 뒤로가기
        setupSwipeBack();

        // 2. 작성 페이지 초기화
        if (document.getElementById('log-create-form')) {
            initLogCreate();
        }

        // 3. 상세 페이지 초기화
        if (document.querySelector('.detail-header')) {
            initLogDetail();
        }

        // 4. 공유 버튼 (공통)
        const shareBtn = document.getElementById('instagramShareBtn');
        if (shareBtn) {
            shareBtn.addEventListener('click', handleInstagramShare);
        }
    });

    /**
     * [작성 페이지] 초기화
     */
    function initLogCreate() {
        const imageUpload = document.getElementById('imageUpload');
        const imageInput = document.getElementById('imageInput');
        const imagePreview = document.getElementById('imagePreview');
        const cookedAt = document.getElementById('cookedAt');

        // 이미지 미리보기
        if (imageUpload && imageInput) {
            imageUpload.addEventListener('click', () => imageInput.click());
            imageInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (!file) return;
                
                // 파일 크기 체크 (10MB)
                if (file.size > 10 * 1024 * 1024) {
                    alert('파일 크기는 10MB 이하여야 합니다.');
                    this.value = '';
                    return;
                }

                const reader = new FileReader();
                reader.onload = (ev) => {
                    imagePreview.src = ev.target.result;
                    imagePreview.style.display = 'block';
                    imageUpload.style.display = 'none';
                };
                reader.readAsDataURL(file);
            });
        }

        // 별점 기능
        setupStarRating('difficultyStars', 'difficultyRating');
        setupStarRating('satisfactionStars', 'satisfactionRating');

        // 오늘 날짜 자동 입력
        if (cookedAt && !cookedAt.value) {
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            cookedAt.value = `${year}-${month}-${day}`;
        }
    }

    /**
     * [상세 페이지] 초기화
     */
    function initLogDetail() {
        const moreBtn = document.getElementById('moreBtn');
        const menu = document.getElementById('optionsMenu');

        if (moreBtn && menu) {
            moreBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                menu.style.display = (menu.style.display === 'none') ? 'block' : 'none';
            });

            // 외부 클릭 시 메뉴 닫기
            document.addEventListener('click', () => {
                menu.style.display = 'none';
            });
        }
    }

    /* ==================== 공통 유틸리티 ==================== */

    // 별점 클릭 로직
    function setupStarRating(containerId, inputId) {
        const container = document.getElementById(containerId);
        const input = document.getElementById(inputId);
        if (!container || !input) return;

        const btns = container.querySelectorAll('.star-btn');
        btns.forEach((btn, index) => {
            btn.addEventListener('click', () => {
                // data-value 값을 input에 저장 (없으면 인덱스+1)
                const value = btn.getAttribute('data-value') || (index + 1);
                input.value = value;

                // UI 색상 업데이트
                btns.forEach((b, i) => {
                    if (i <= index) b.classList.add('active');
                    else b.classList.remove('active');
                });
            });
        });
    }

    // 인스타그램 공유 (클립보드 복사)
    function handleInstagramShare() {
        const currentUrl = window.location.href;
        if (navigator.clipboard) {
            navigator.clipboard.writeText(currentUrl).then(() => {
                alert('링크가 복사되었습니다! 인스타그램에 공유해보세요.');
            });
        } else {
            alert('이 브라우저는 링크 복사를 지원하지 않습니다.');
        }
    }

    // 스와이프 뒤로가기
    function setupSwipeBack() {
        let touchStartX = 0;
        let touchEndX = 0;
        
        document.addEventListener('touchstart', e => { touchStartX = e.changedTouches[0].screenX; }, false);
        document.addEventListener('touchend', e => {
            touchEndX = e.changedTouches[0].screenX;
            // 왼쪽 끝(50px)에서 시작해서 오른쪽으로 50px 이상 스와이프 시
            if (touchEndX > touchStartX + 50 && touchStartX < 50) {
                window.history.back();
            }
        }, false);
    }

})();

// ★ [추가] 삭제 버튼 클릭 시 실행되는 함수 (전역)
window.deleteLog = function() {
    if (confirm('정말 이 일지를 삭제하시겠습니까?')) {
        const form = document.getElementById('deleteForm');
        if (form) {
            form.submit(); // 숨겨진 폼 제출 (POST 요청)
        } else {
            alert("삭제 처리 중 오류가 발생했습니다.");
        }
    }
    // 메뉴 닫기
    const menu = document.getElementById('optionsMenu');
    if(menu) menu.style.display = 'none';
};