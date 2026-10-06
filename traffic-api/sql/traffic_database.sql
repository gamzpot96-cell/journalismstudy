-- ============================================================
-- ITS 교통정보 프로젝트 MySQL 데이터베이스
-- 파일명: traffic_database.sql
-- ============================================================


-- ============================================================
-- 1. 데이터베이스 생성
-- ============================================================

CREATE DATABASE IF NOT EXISTS traffic_database
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;


-- 사용할 데이터베이스 선택
USE traffic_database;


-- ============================================================
-- 2. 기존 테이블이 있다면 삭제
-- ============================================================

DROP TABLE IF EXISTS traffic_information;


-- ============================================================
-- 3. 교통정보 테이블 생성
-- ============================================================

CREATE TABLE traffic_information (
    
    -- 교통정보 고유 번호
    traffic_id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- 도로 이름
    road_name VARCHAR(100) NOT NULL,
    
    -- 도로 종류
    road_type VARCHAR(50),
    
    -- 현재 차량 평균 속도(km/h)
    speed INT,
    
    -- 예상 통행 시간(분)
    travel_time INT,
    
    -- 교통 상태
    traffic_status VARCHAR(20),
    
    -- 위도
    latitude DECIMAL(10, 7),
    
    -- 경도
    longitude DECIMAL(10, 7),
    
    -- 교통정보 수집 시간
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 4. 테스트 데이터 입력
-- ============================================================

INSERT INTO traffic_information
    (
        road_name,
        road_type,
        speed,
        travel_time,
        traffic_status,
        latitude,
        longitude
    )
VALUES
    (
        '강남대로',
        '일반도로',
        65,
        10,
        '원활',
        37.4979000,
        127.0276000
    ),
    (
        '테헤란로',
        '일반도로',
        35,
        18,
        '서행',
        37.4981000,
        127.0282000
    ),
    (
        '올림픽대로',
        '도시고속도로',
        20,
        25,
        '정체',
        37.5190000,
        127.0410000
    ),
    (
        '강변북로',
        '도시고속도로',
        45,
        15,
        '서행',
        37.5350000,
        127.0100000
    ),
    (
        '서울로',
        '일반도로',
        70,
        8,
        '원활',
        37.5547000,
        126.9717000
    );


-- ============================================================
-- 5. 전체 교통정보 조회
-- ============================================================

SELECT *
FROM traffic_information;


-- ============================================================
-- 6. 도로명과 현재 속도만 조회
-- ============================================================

SELECT
    road_name,
    speed,
    traffic_status
FROM traffic_information;


-- ============================================================
-- 7. 교통 상태가 '정체'인 도로 조회
-- ============================================================

SELECT
    road_name,
    speed,
    travel_time,
    traffic_status
FROM traffic_information
WHERE traffic_status = '정체';


-- ============================================================
-- 8. 현재 속도가 40km/h 이하인 도로 조회
-- ============================================================

SELECT
    road_name,
    speed,
    traffic_status
FROM traffic_information
WHERE speed <= 40;


-- ============================================================
-- 9. 속도가 빠른 도로부터 정렬
-- ============================================================

SELECT
    road_name,
    speed,
    traffic_status
FROM traffic_information
ORDER BY speed DESC;


-- ============================================================
-- 10. 교통정보 개수 확인
-- ============================================================

SELECT COUNT(*) AS traffic_count
FROM traffic_information;


-- ============================================================
-- 11. 교통 상태별 도로 개수 확인
-- ============================================================

SELECT
    traffic_status,
    COUNT(*) AS road_count
FROM traffic_information
GROUP BY traffic_status;


-- ============================================================
-- 12. 특정 데이터 수정 예제
-- ============================================================

UPDATE traffic_information
SET
    speed = 30,
    traffic_status = '서행'
WHERE traffic_id = 3;


-- 수정 결과 확인
SELECT *
FROM traffic_information
WHERE traffic_id = 3;


-- ============================================================
-- 13. 특정 데이터 삭제 예제
-- ============================================================

-- 아래 SQL은 실제 데이터를 삭제하므로
-- 연습할 때 필요한 경우에만 실행하세요.

-- DELETE FROM traffic_information
-- WHERE traffic_id = 5;


-- ============================================================
-- 14. 최종 데이터 확인
-- ============================================================

SELECT
    traffic_id,
    road_name,
    road_type,
    speed,
    travel_time,
    traffic_status,
    latitude,
    longitude,
    collected_at
FROM traffic_information
ORDER BY traffic_id;

SHOW DATABASES;
SHOW TABLES;
DESCRIBE traffic_information;