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
        // const shareBtn = document.getElementById('instagramShareBtn');
        // if (shareBtn) {
        //     shareBtn.addEventListener('click', handleInstagramShare);
        // }
    });

    /**
     * [작성 페이지] 초기화
     */
    function initLogCreate() {
        const form = document.getElementById('log-create-form');
        const imageUpload = document.getElementById('imageUpload');
        const imageInput = document.getElementById('imageInput');
        const imagePreview = document.getElementById('imagePreview');
        const cookedAt = document.getElementById('cookedAt');
        const isEdit = form && form.getAttribute('data-is-edit') === 'true';

        // 수정 페이지: 이전 버튼 클릭 시 수정 사항 있으면 확인
        let formDirty = false;
        if (isEdit && form) {
            const backBtn = document.getElementById('logBackBtn');
            const diffInput = document.getElementById('difficultyRating');
            const ratingInput = document.getElementById('satisfactionRating');
            const memoInput = form.querySelector('textarea[name="memo"]');

            function checkDirty() {
                const diffChanged = diffInput && diffInput.value !== (diffInput.getAttribute('data-initial') || '');
                const ratingChanged = ratingInput && ratingInput.value !== (ratingInput.getAttribute('data-initial') || '');
                const memoChanged = memoInput && memoInput.value !== (memoInput.getAttribute('data-initial') || '');
                const dateChanged = cookedAt && cookedAt.value !== (cookedAt.getAttribute('data-initial') || '');
                const imageChanged = imageInput && imageInput.files && imageInput.files.length > 0;
                const removeImageInput = document.getElementById('removeImageInput');
                const imageRemoved = removeImageInput && removeImageInput.value === '1';
                formDirty = !!(diffChanged || ratingChanged || memoChanged || dateChanged || imageChanged || imageRemoved);
            }

            if (diffInput) diffInput.setAttribute('data-initial', diffInput.value || '');
            if (ratingInput) ratingInput.setAttribute('data-initial', ratingInput.value || '');
            if (memoInput) memoInput.setAttribute('data-initial', memoInput.value || '');
            if (cookedAt) cookedAt.setAttribute('data-initial', cookedAt.value || '');

            form.addEventListener('input', checkDirty);
            form.addEventListener('change', checkDirty);
            if (imageInput) imageInput.addEventListener('change', checkDirty);

            if (backBtn) {
                backBtn.addEventListener('click', function() {
                    checkDirty();
                    if (formDirty && confirm('수정 사항이 있습니다. 저장하고 종료하시겠어요?')) {
                        form.submit();
                    } else {
                        window.history.back();
                    }
                });
            }
        } else {
            const backBtn = document.getElementById('logBackBtn');
            if (backBtn) backBtn.addEventListener('click', function() { window.history.back(); });
        }

        // 이미지 미리보기 및 수정하기 (클릭 시 파일 선택)
        const imagePreviewWrap = document.getElementById('imagePreviewWrap');
        const imageDeleteBtn = document.getElementById('imageDeleteBtn');
        const removeImageInput = document.getElementById('removeImageInput');
        if (imageUpload && imageInput) {
            imageUpload.addEventListener('click', () => imageInput.click());
            if (imagePreviewWrap) {
                imagePreviewWrap.addEventListener('click', (e) => {
                    if (e.target.closest('#imageDeleteBtn')) return;
                    imageInput.click();
                });
            }
            if (imagePreview) {
                imagePreview.addEventListener('click', (e) => { e.preventDefault(); imageInput.click(); });
            }
            // 사진 삭제 버튼 (수정 페이지)
            if (imageDeleteBtn && removeImageInput && isEdit) {
                imageDeleteBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (this.dataset.hasImage !== 'true') {
                        alert('삭제할 사진이 없습니다.');
                        return;
                    }
                    removeImageInput.value = '1';
                    if (imagePreviewWrap) imagePreviewWrap.style.display = 'none';
                    if (imageUpload) imageUpload.style.display = 'flex';
                    imageInput.value = '';
                    if (imagePreview) imagePreview.src = '';
                    this.dataset.hasImage = 'false';
                    this.style.opacity = '0.5';
                    formDirty = true;
                });
            }
            imageInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (!file) return;
                
                // 파일 크기 체크 (10MB)
                if (file.size > 10 * 1024 * 1024) {
                    alert('파일 크기는 10MB 이하여야 합니다.');
                    this.value = '';
                    return;
                }

                if (removeImageInput) removeImageInput.value = '0';
                const reader = new FileReader();
                reader.onload = (ev) => {
                    imagePreview.src = ev.target.result;
                    imagePreview.style.display = 'block';
                    if (imagePreviewWrap) imagePreviewWrap.style.display = 'flex';
                    if (imageUpload) imageUpload.style.display = 'none';
                };
                reader.readAsDataURL(file);
            });
        }

        // 별점 기능 (난이도·만족도 모두 5개 별)
        setupStarRating('difficultyStars', 'difficultyRating');
        setupStarRating('satisfactionStars', 'satisfactionRating');

        // 난이도 (숫자 선택 시 EASY/NORMAL/DIFFICULT로 변환, 미선택 시 기본값 유지)
        if (form) {
            form.addEventListener('submit', function() {
                const diffInput = document.getElementById('difficultyRating');
                if (!diffInput) return;
                const val = (diffInput.value || '').trim();
                if (val === 'EASY' || val === 'NORMAL' || val === 'DIFFICULT') return;
                if (!val) {
                    diffInput.value = 'NORMAL';
                    return;
                }
                const n = parseInt(val, 10);
                if (n <= 2) diffInput.value = 'EASY';
                else if (n === 3) diffInput.value = 'NORMAL';
                else diffInput.value = 'DIFFICULT';
            });
        }

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
    // function handleInstagramShare() {
    //     const currentUrl = window.location.href;
    //     if (navigator.clipboard) {
    //         navigator.clipboard.writeText(currentUrl).then(() => {
    //             alert('링크가 복사되었습니다! 인스타그램에 공유해보세요.');
    //         });
    //     } else {
    //         alert('이 브라우저는 링크 복사를 지원하지 않습니다.');
    //     }
    // }

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

// 일지 상세 페이지 - 삭제 버튼
window.deleteLog = function() {
    if (confirm('정말 이 일지를 삭제하시겠습니까?')) {
        const form = document.getElementById('deleteForm');
        if (form) form.submit();
        else alert('삭제 처리 중 오류가 발생했습니다.');
    }
    const menu = document.getElementById('optionsMenu');
    if (menu) menu.style.display = 'none';
};