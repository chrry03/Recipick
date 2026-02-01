/**
 * 일지 작성 페이지 JavaScript
 */

(function() {
    'use strict';

    // DOM 요소
    const elements = {
        form: null,
        imageUpload: null,
        imageInput: null,
        imagePreview: null,
        difficultyStars: null,
        satisfactionStars: null,
        difficultyRating: null,
        satisfactionRating: null,
        memoInput: null,
        cookedAt: null,
        submitBtn: null,
        recipeName: null
    };

    // 상태
    const state = {
        difficultyRating: 0,
        satisfactionRating: 0
    };

    /**
     * 초기화
     */
    function init() {
        // DOM 요소 가져오기
        elements.form = document.getElementById('log-create-form');
        elements.imageUpload = document.getElementById('imageUpload');
        elements.imageInput = document.getElementById('imageInput');
        elements.imagePreview = document.getElementById('imagePreview');
        elements.difficultyStars = document.getElementById('difficultyStars');
        elements.satisfactionStars = document.getElementById('satisfactionStars');
        elements.difficultyRating = document.getElementById('difficultyRating');
        elements.satisfactionRating = document.getElementById('satisfactionRating');
        elements.memoInput = document.getElementById('memoInput');
        elements.cookedAt = document.getElementById('cookedAt');
        elements.submitBtn = document.getElementById('submitBtn');
        elements.recipeName = document.getElementById('recipeName');

        // 이벤트 리스너 등록
        initImageUpload();
        initStarRatings();
        initDateInput();
        initFormSubmit();
    }

    /**
     * 이미지 업로드 초기화
     */
    function initImageUpload() {
        if (!elements.imageUpload || !elements.imageInput || !elements.imagePreview) return;

        elements.imageUpload.addEventListener('click', () => {
            elements.imageInput.click();
        });

        elements.imageInput.addEventListener('change', handleImageSelect);
    }

    /**
     * 이미지 선택 처리
     */
    function handleImageSelect(e) {
        const file = e.target.files[0];
        if (!file) return;

        // 파일 크기 검증 (10MB 제한)
        if (file.size > 10 * 1024 * 1024) {
            alert('파일 크기는 10MB 이하여야 합니다.');
            return;
        }

        // 파일 타입 검증
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
     * 별점 평가 초기화
     */
    function initStarRatings() {
        if (elements.difficultyStars) {
            initRatingGroup(elements.difficultyStars, 'difficulty');
        }
        if (elements.satisfactionStars) {
            initRatingGroup(elements.satisfactionStars, 'satisfaction');
        }
    }

    /**
     * 별점 그룹 초기화
     */
    function initRatingGroup(container, type) {
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
     * 날짜 입력 초기화
     */
    function initDateInput() {
        if (!elements.cookedAt) return;

        // 오늘 날짜를 기본값으로 설정
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        elements.cookedAt.value = `${year}-${month}-${day}`;
    }

    /**
     * 폼 제출 초기화
     */
    function initFormSubmit() {
        if (!elements.form) return;

        elements.form.addEventListener('submit', handleFormSubmit);
    }

    /**
     * 폼 제출 처리
     */
    async function handleFormSubmit(e) {
        e.preventDefault();

        // 유효성 검사
        if (!validateForm()) {
            return;
        }

        // 제출 버튼 비활성화
        setSubmitButtonState(true);

        try {
            const formData = new FormData(elements.form);
            
            // TODO: 실제 API 호출로 교체
            console.log('일지 저장 데이터:', {
                recipe_name: elements.recipeName?.textContent || '',
                difficulty_rating: state.difficultyRating,
                satisfaction_rating: state.satisfactionRating,
                memo: elements.memoInput?.value || '',
                cooked_at: elements.cookedAt?.value || '',
                image: elements.imageInput?.files[0] ? '파일 업로드됨' : '없음'
            });

            // 임시 성공 메시지
            alert('일지가 작성되었습니다!');
            
            // 실제 API 호출 예시:
            // const response = await fetch('/api/logs/create/', {
            //     method: 'POST',
            //     headers: {
            //         'X-CSRFToken': getCSRFToken()
            //     },
            //     body: formData
            // });
            //
            // if (response.ok) {
            //     const data = await response.json();
            //     alert('일지가 저장되었습니다.');
            //     window.location.href = '/logs/';
            // } else {
            //     const error = await response.json();
            //     alert(error.message || '일지 저장에 실패했습니다.');
            // }
        } catch (error) {
            console.error('일지 저장 오류:', error);
            alert('일지 저장 중 오류가 발생했습니다.');
        } finally {
            setSubmitButtonState(false);
        }
    }

    /**
     * 폼 유효성 검사
     */
    function validateForm() {
        if (state.difficultyRating === 0) {
            alert('난이도를 선택해주세요.');
            return false;
        }

        if (state.satisfactionRating === 0) {
            alert('만족도를 선택해주세요.');
            return false;
        }

        return true;
    }

    /**
     * 제출 버튼 상태 설정
     */
    function setSubmitButtonState(disabled) {
        if (!elements.submitBtn) return;

        elements.submitBtn.disabled = disabled;
        if (disabled) {
            elements.submitBtn.textContent = '저장 중...';
        } else {
            elements.submitBtn.textContent = '작성하기';
        }
    }

    /**
     * CSRF 토큰 가져오기
     */
    function getCSRFToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfToken ? csrfToken.value : '';
    }

    // DOM 로드 완료 시 초기화
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
