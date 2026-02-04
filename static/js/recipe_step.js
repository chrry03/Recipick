/**
 * 레시피 단계 네비게이션 모듈
 * 요리 과정 단계별 페이지에서 사용되는 네비게이션 기능 제공
 */
(function() {
    'use strict';

    /**
     * RecipeStepNavigator 클래스
     * 레시피 단계 네비게이션을 관리하는 클래스
     */
    class RecipeStepNavigator {
        constructor(options = {}) {
            this.currentStep = this._getCurrentStep();
            this.totalSteps = options.totalSteps || this._getTotalSteps();
            this.recipeId = options.recipeId || this._getRecipeId();
            this.baseUrl = options.baseUrl || '/recipes';
            this.swipeThreshold = options.swipeThreshold || 50;
            
            this.touchStartX = 0;
            this.touchEndX = 0;
            
            this._init();
        }

        /**
         * 현재 단계 번호 추출
         * @returns {number} 현재 단계 번호
         */
        _getCurrentStep() {
            const stepElement = document.querySelector('.step-number p');
            if (stepElement) {
                const stepText = stepElement.textContent.trim();
                const stepNumber = parseInt(stepText, 10);
                return isNaN(stepNumber) ? 1 : stepNumber;
            }
            return 1;
        }

        /**
         * 총 단계 수 추출 (데이터 속성 또는 DOM에서)
         * @returns {number} 총 단계 수
         */
        _getTotalSteps() {
            const container = document.querySelector('.recipe-container');
            if (container && container.dataset.totalSteps) {
                return parseInt(container.dataset.totalSteps, 10);
            }
            // 기본값 또는 다른 방법으로 추출
            return 5; // 기본값
        }

        /**
         * 레시피 ID 추출
         * @returns {string|null} 레시피 ID
         */
        _getRecipeId() {
            const container = document.querySelector('.recipe-container');
            if (container && container.dataset.recipeId) {
                console.log('레시피 ID (data 속성):', container.dataset.recipeId);
                return container.dataset.recipeId;
            }
            // URL에서 추출 시도
            const match = window.location.pathname.match(/\/recipes\/(\d+)\//);
            const recipeId = match ? match[1] : null;
            console.log('레시피 ID (URL에서 추출):', recipeId, '현재 경로:', window.location.pathname);
            return recipeId;
        }

        /**
         * 초기화
         */
        _init() {
            this._bindEvents();
            this._updateButtonStates();
        }

        /**
         * 이벤트 바인딩
         */
        _bindEvents() {
            // 버튼 클릭 이벤트
            const prevBtn = document.querySelector('.btn-prev');
            const nextBtn = document.querySelector('.btn-next');
            const exitBtn = document.querySelector('.btn-exit');
            
            if (prevBtn) {
                prevBtn.addEventListener('click', () => this.goToPrevStep());
            }
            
            if (nextBtn) {
                nextBtn.addEventListener('click', () => this.goToNextStep());
            }
            
            if (exitBtn) {
                exitBtn.addEventListener('click', () => this.exitCooking());
            }

            // 키보드 네비게이션
            document.addEventListener('keydown', (e) => this._handleKeydown(e));
            
            // 터치 스와이프 (모바일)
            document.addEventListener('touchstart', (e) => this._handleTouchStart(e));
            document.addEventListener('touchend', (e) => this._handleTouchEnd(e));
        }

        /**
         * 키보드 이벤트 처리
         * @param {KeyboardEvent} event 키보드 이벤트
         */
        _handleKeydown(event) {
            // 입력 필드에 포커스가 있으면 무시
            if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                return;
            }

            if (event.key === 'ArrowLeft') {
                event.preventDefault();
                this.goToPrevStep();
            } else if (event.key === 'ArrowRight') {
                event.preventDefault();
                this.goToNextStep();
            }
        }

        /**
         * 터치 시작 이벤트 처리
         * @param {TouchEvent} event 터치 이벤트
         */
        _handleTouchStart(event) {
            this.touchStartX = event.changedTouches[0].screenX;
        }

        /**
         * 터치 종료 이벤트 처리
         * @param {TouchEvent} event 터치 이벤트
         */
        _handleTouchEnd(event) {
            this.touchEndX = event.changedTouches[0].screenX;
            this._handleSwipe();
        }

        /**
         * 스와이프 제스처 처리
         */
        _handleSwipe() {
            const diffX = this.touchStartX - this.touchEndX;
            
            if (Math.abs(diffX) < this.swipeThreshold) {
                return; // 스와이프 거리가 충분하지 않음
            }

            if (diffX > 0) {
                // 왼쪽으로 스와이프 - 다음 단계
                this.goToNextStep();
            } else {
                // 오른쪽으로 스와이프 - 이전 단계
                this.goToPrevStep();
            }
        }

        /**
         * 이전 단계로 이동
         */
        goToPrevStep() {
            if (this.currentStep <= 1) {
                console.log('첫 번째 단계입니다.');
                return;
            }

            const prevStep = this.currentStep - 1;
            this._navigateToStep(prevStep);
        }

        /**
         * 다음 단계로 이동
         */
        goToNextStep() {
            if (this.currentStep >= this.totalSteps) {
                console.log('마지막 단계입니다.');
                return;
            }

            const nextStep = this.currentStep + 1;
            this._navigateToStep(nextStep);
        }

        /**
         * 특정 단계로 이동
         * @param {number} step 단계 번호
         */
        _navigateToStep(step) {
            if (step < 1 || step > this.totalSteps) {
                console.error(`유효하지 않은 단계 번호: ${step}`);
                return;
            }

            try {
                // URL 생성
                const url = this._buildStepUrl(step);
                console.log('이동할 URL:', url); // 디버깅용
                
                // 페이지 이동
                window.location.href = url;
            } catch (error) {
                console.error('단계 이동 중 오류 발생:', error);
            }
        }

        /**
         * 단계 URL 생성
         * @param {number} step 단계 번호
         * @returns {string} 단계 URL
         */
        _buildStepUrl(step) {
            console.log('URL 생성 - recipeId:', this.recipeId, 'step:', step, 'baseUrl:', this.baseUrl); // 디버깅용
            
            if (this.recipeId) {
                // 모든 단계는 step/{step}/ 형식으로 통일
                const url = `${this.baseUrl}/${this.recipeId}/step/${step}/`;
                console.log('생성된 URL:', url);
                return url;
            }
            // 레시피 ID가 없으면 단계만 사용
            const url = `${this.baseUrl}/step/${step}/`;
            console.log('생성된 URL (no recipeId):', url);
            return url;
        }

        /**
         * 요리 종료하고 홈으로 이동
         */
        exitCooking() {
            window.location.href = '/main/';
        }

        /**
         * 버튼 상태 업데이트
         */
        _updateButtonStates() {
            const prevBtn = document.querySelector('.btn-prev');
            const nextBtn = document.querySelector('.btn-next');
            const exitBtn = document.querySelector('.btn-exit');

            // 이전 버튼은 2단계 이상일 때만 표시되므로 여기서는 처리하지 않음
            // (템플릿에서 조건부 렌더링으로 처리)

            if (nextBtn) {
                if (this.currentStep >= this.totalSteps) {
                    nextBtn.disabled = true;
                    nextBtn.classList.add('disabled');
                } else {
                    nextBtn.disabled = false;
                    nextBtn.classList.remove('disabled');
                }
            }
        }
    }

    // 전역 함수로 노출 (기존 코드와의 호환성을 위해)
    window.goToPrevStep = function() {
        if (window.recipeStepNavigator) {
            window.recipeStepNavigator.goToPrevStep();
        }
    };

    window.goToNextStep = function() {
        if (window.recipeStepNavigator) {
            window.recipeStepNavigator.goToNextStep();
        }
    };

    // DOMContentLoaded 시 초기화
    function initNavigator() {
        const container = document.querySelector('.recipe-container');
        if (container) {
            console.log('RecipeStepNavigator 초기화 시작');
            window.recipeStepNavigator = new RecipeStepNavigator();
            console.log('RecipeStepNavigator 초기화 완료', window.recipeStepNavigator);
        } else {
            console.warn('.recipe-container를 찾을 수 없습니다.');
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNavigator);
    } else {
        // 이미 로드된 경우
        initNavigator();
    }

})();
