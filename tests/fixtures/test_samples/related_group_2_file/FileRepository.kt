package sirius.appius.modules.file.service

import org.springframework.data.mongodb.repository.Query
import org.springframework.data.repository.kotlin.CoroutineCrudRepository
import org.springframework.stereotype.Repository
import java.time.ZonedDateTime
import java.util.UUID

/**
 * 파일 정보 저장소 인터페이스
 *
 * MongoDB를 사용한 비동기 파일 메타데이터 접근 계층
 *
 * 특징:
 * - 대용량 파일 메타데이터 관리에 최적화
 * - 유연한 스키마로 다양한 파일 속성 저장
 * - GridFS 연동 지원 (대용량 파일의 경우)
 *
 * @author File Team
 * @since 2024-01-01
 */
@Repository
interface FileRepository : CoroutineCrudRepository<FileInfo, UUID> {

    /**
     * 원본 파일명으로 파일을 검색합니다.
     *
     * @param originalFileName 원본 파일명
     * @return 파일 목록
     */
    @Query("{ 'originalFileName': { \$regex: ?0, \$options: 'i' } }")
    suspend fun findByOriginalFileNameContaining(originalFileName: String): List<FileInfo>

    /**
     * 저장된 파일명으로 파일을 조회합니다.
     *
     * @param storedFileName 저장된 파일명
     * @return 파일 정보 (없으면 null)
     */
    @Query("{ 'storedFileName': ?0 }")
    suspend fun findByStoredFileName(storedFileName: String): FileInfo?

    /**
     * 카테고리별 파일 목록을 조회합니다.
     *
     * @param category 파일 카테고리
     * @param uploaderId 업로더 ID (선택)
     * @return 파일 목록
     */
    @Query(
        """
        {
            'category': ?0,
            'status': 'ACTIVE',
            ${'$'}and: [
                { ${'$'}or: [ { 'uploaderId': ?1 }, { ?1: null } ] }
            ]
        }
        """
    )
    suspend fun findByCategory(
        category: FileCategory,
        uploaderId: UUID? = null
    ): List<FileInfo>

    /**
     * 업로더별 파일 목록을 조회합니다.
     *
     * @param uploaderId 업로더 ID
     * @return 파일 목록
     */
    @Query("{ 'uploaderId': ?0, 'status': 'ACTIVE' }")
    suspend fun findByUploaderId(uploaderId: UUID): List<FileInfo>

    /**
     * 연관 엔티티의 파일 목록을 조회합니다.
     *
     * @param relatedEntityId 연관 엔티티 ID
     * @return 파일 목록
     */
    @Query("{ 'relatedEntityId': ?0, 'status': 'ACTIVE' }")
    suspend fun findByRelatedEntityId(relatedEntityId: UUID): List<FileInfo>

    /**
     * 특정 기간에 업로드된 파일 목록을 조회합니다.
     *
     * @param startDate 시작일
     * @param endDate 종료일
     * @return 파일 목록
     */
    @Query(
        """
        {
            'createdAt': { ${'$'}gte: ?0, ${'$'}lte: ?1 },
            'status': 'ACTIVE'
        }
        """
    )
    suspend fun findByUploadPeriod(
        startDate: ZonedDateTime,
        endDate: ZonedDateTime
    ): List<FileInfo>

    /**
     * 임시 파일 목록을 조회합니다.
     * (정리 대상 파일)
     *
     * @param olderThan 이 시간보다 오래된 파일
     * @return 임시 파일 목록
     */
    @Query(
        """
        {
            'status': 'TEMPORARY',
            'createdAt': { ${'$'}lt: ?0 }
        }
        """
    )
    suspend fun findTemporaryFiles(olderThan: ZonedDateTime): List<FileInfo>

    /**
     * 삭제된 파일 목록을 조회합니다.
     *
     * @param deletedAfter 이 시간 이후 삭제된 파일
     * @return 삭제된 파일 목록
     */
    @Query(
        """
        {
            'status': 'DELETED',
            'deletedAt': { ${'$'}gte: ?0 }
        }
        """
    )
    suspend fun findDeletedFiles(deletedAfter: ZonedDateTime): List<FileInfo>

    /**
     * 파일 크기 범위로 파일을 검색합니다.
     *
     * @param minSize 최소 크기 (바이트)
     * @param maxSize 최대 크기 (바이트)
     * @return 파일 목록
     */
    @Query(
        """
        {
            'fileSize': { ${'$'}gte: ?0, ${'$'}lte: ?1 },
            'status': 'ACTIVE'
        }
        """
    )
    suspend fun findByFileSizeRange(minSize: Long, maxSize: Long): List<FileInfo>

    /**
     * 특정 확장자의 파일 목록을 조회합니다.
     *
     * @param extension 파일 확장자
     * @return 파일 목록
     */
    @Query("{ 'extension': ?0, 'status': 'ACTIVE' }")
    suspend fun findByExtension(extension: String): List<FileInfo>

    /**
     * 카테고리별 파일 개수를 조회합니다.
     *
     * @param category 파일 카테고리
     * @return 파일 개수
     */
    @Query("{ 'category': ?0, 'status': 'ACTIVE' }")
    suspend fun countByCategory(category: FileCategory): Long

    /**
     * 총 파일 크기를 계산합니다.
     *
     * @param uploaderId 업로더 ID (선택)
     * @return 총 파일 크기 (바이트)
     */
    suspend fun calculateTotalFileSize(uploaderId: UUID? = null): Long

    /**
     * 파일 정보를 업데이트합니다.
     *
     * @param fileInfo 업데이트할 파일 정보
     * @return 업데이트된 파일 정보
     */
    suspend fun update(fileInfo: FileInfo): FileInfo {
        return save(fileInfo)
    }
}

/**
 * 파일 통계 데이터 DTO
 */
data class FileStatistics(
    val totalCount: Long,
    val totalSize: Long,
    val countByCategory: Map<FileCategory, Long>,
    val averageFileSize: Long
)

/**
 * 파일 저장소 확장 인터페이스
 *
 * 복잡한 집계 쿼리를 위한 커스텀 메서드 정의
 */
@Repository
interface FileRepositoryCustom {

    /**
     * 파일 통계를 조회합니다.
     *
     * @param startDate 시작일 (선택)
     * @param endDate 종료일 (선택)
     * @return 파일 통계
     */
    suspend fun getFileStatistics(
        startDate: ZonedDateTime? = null,
        endDate: ZonedDateTime? = null
    ): FileStatistics

    /**
     * 가장 많이 업로드한 사용자 목록을 조회합니다.
     *
     * @param limit 조회 개수
     * @return 사용자 ID와 파일 개수 맵
     */
    suspend fun getTopUploaders(limit: Int = 10): Map<UUID, Long>

    /**
     * 가장 큰 파일 목록을 조회합니다.
     *
     * @param limit 조회 개수
     * @return 파일 목록
     */
    suspend fun getLargestFiles(limit: Int = 10): List<FileInfo>

    /**
     * 사용되지 않는 파일 목록을 조회합니다.
     * (relatedEntityId가 없고 일정 기간 지난 파일)
     *
     * @param unusedDays 미사용 기간 (일)
     * @return 미사용 파일 목록
     */
    suspend fun findUnusedFiles(unusedDays: Int = 30): List<FileInfo>
}
