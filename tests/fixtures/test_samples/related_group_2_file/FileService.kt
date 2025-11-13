package sirius.appius.modules.file.service

import io.github.oshai.kotlinlogging.KotlinLogging
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import org.springframework.web.multipart.MultipartFile
import java.time.ZonedDateTime
import java.util.UUID

/**
 * 파일 관리 서비스
 *
 * 주요 책임:
 * - 파일 업로드/다운로드
 * - 파일 메타데이터 관리
 * - 파일 접근 권한 검증
 * - 임시 파일 정리
 *
 * 지원 파일 타입:
 * - 이미지: JPG, PNG, GIF (최대 10MB)
 * - 문서: PDF, DOCX, XLSX (최대 50MB)
 * - 기타: ZIP, CSV (최대 100MB)
 *
 * @author File Team
 * @since 2024-01-01
 */
@Service
class FileService(
    private val fileRepository: FileRepository,
    private val fileStorageProvider: FileStorageProvider,
    private val fileValidator: FileValidator,
    private val thumbnailGenerator: ThumbnailGenerator
) {
    private val log = KotlinLogging.logger {}

    companion object {
        // 허용된 파일 확장자
        private val ALLOWED_IMAGE_EXTENSIONS = setOf("jpg", "jpeg", "png", "gif")
        private val ALLOWED_DOCUMENT_EXTENSIONS = setOf("pdf", "docx", "xlsx", "csv")
        private val ALLOWED_ARCHIVE_EXTENSIONS = setOf("zip")

        // 파일 크기 제한 (바이트)
        private const val MAX_IMAGE_SIZE = 10 * 1024 * 1024L      // 10MB
        private const val MAX_DOCUMENT_SIZE = 50 * 1024 * 1024L   // 50MB
        private const val MAX_ARCHIVE_SIZE = 100 * 1024 * 1024L   // 100MB
    }

    /**
     * 파일을 업로드합니다.
     *
     * @param file 업로드할 파일
     * @param uploaderId 업로드한 사용자 ID
     * @param category 파일 카테고리 (주문서, 인수증 등)
     * @param relatedEntityId 연관 엔티티 ID (선택)
     * @return 업로드된 파일 정보
     */
    @Transactional
    suspend fun uploadFile(
        file: MultipartFile,
        uploaderId: UUID,
        category: FileCategory,
        relatedEntityId: UUID? = null
    ): FileInfo {
        log.info { "파일 업로드 시작: filename=${file.originalFilename}, uploaderId=$uploaderId" }

        // 파일 유효성 검증
        fileValidator.validate(file)

        // 파일 확장자 추출
        val extension = getFileExtension(file.originalFilename ?: "unknown")
        val contentType = file.contentType ?: "application/octet-stream"

        // 고유 파일명 생성
        val storedFileName = generateStoredFileName(extension)

        // 스토리지에 파일 저장
        val storageUrl = fileStorageProvider.store(
            file = file,
            storedFileName = storedFileName,
            category = category
        )

        // 이미지인 경우 썸네일 생성
        val thumbnailUrl = if (isImageFile(extension)) {
            thumbnailGenerator.generate(file, storedFileName)
        } else null

        // 파일 메타데이터 저장
        val fileInfo = FileInfo(
            id = UUID.randomUUID(),
            originalFileName = file.originalFilename ?: "unknown",
            storedFileName = storedFileName,
            fileSize = file.size,
            contentType = contentType,
            extension = extension,
            category = category,
            storageUrl = storageUrl,
            thumbnailUrl = thumbnailUrl,
            uploaderId = uploaderId,
            relatedEntityId = relatedEntityId,
            status = FileStatus.ACTIVE,
            createdAt = ZonedDateTime.now(),
            updatedAt = ZonedDateTime.now()
        )

        val savedFileInfo = fileRepository.save(fileInfo)

        log.info { "파일 업로드 완료: fileId=${savedFileInfo.id}, storageUrl=$storageUrl" }
        return savedFileInfo
    }

    /**
     * 파일 정보를 조회합니다.
     *
     * @param fileId 파일 ID
     * @param requesterId 요청자 ID (권한 검증용)
     * @return 파일 정보
     */
    suspend fun getFileInfo(fileId: UUID, requesterId: UUID): FileInfo {
        log.debug { "파일 정보 조회: fileId=$fileId, requesterId=$requesterId" }

        val fileInfo = fileRepository.findById(fileId)
            ?: throw FileNotFoundException("파일을 찾을 수 없습니다: $fileId")

        // 접근 권한 검증
        if (!canAccess(fileInfo, requesterId)) {
            throw FileAccessDeniedException("파일 접근 권한이 없습니다: $fileId")
        }

        return fileInfo
    }

    /**
     * 파일을 삭제합니다. (논리 삭제)
     *
     * @param fileId 파일 ID
     * @param deleterId 삭제자 ID
     */
    @Transactional
    suspend fun deleteFile(fileId: UUID, deleterId: UUID) {
        log.info { "파일 삭제: fileId=$fileId, deleterId=$deleterId" }

        val fileInfo = fileRepository.findById(fileId)
            ?: throw FileNotFoundException("파일을 찾을 수 없습니다: $fileId")

        // 삭제 권한 검증
        if (!canDelete(fileInfo, deleterId)) {
            throw FileAccessDeniedException("파일 삭제 권한이 없습니다: $fileId")
        }

        // 논리 삭제 처리
        fileInfo.status = FileStatus.DELETED
        fileInfo.deletedAt = ZonedDateTime.now()
        fileInfo.deletedBy = deleterId
        fileInfo.updatedAt = ZonedDateTime.now()

        fileRepository.update(fileInfo)

        log.info { "파일 삭제 완료: fileId=$fileId" }
    }

    /**
     * 카테고리별 파일 목록을 조회합니다.
     *
     * @param category 파일 카테고리
     * @param uploaderId 업로더 ID (선택)
     * @return 파일 목록
     */
    suspend fun findFilesByCategory(
        category: FileCategory,
        uploaderId: UUID? = null
    ): List<FileInfo> {
        log.debug { "카테고리별 파일 조회: category=$category, uploaderId=$uploaderId" }
        return fileRepository.findByCategory(category, uploaderId)
    }

    /**
     * 연관 엔티티의 파일 목록을 조회합니다.
     *
     * @param relatedEntityId 연관 엔티티 ID
     * @return 파일 목록
     */
    suspend fun findFilesByRelatedEntity(relatedEntityId: UUID): List<FileInfo> {
        log.debug { "연관 엔티티 파일 조회: relatedEntityId=$relatedEntityId" }
        return fileRepository.findByRelatedEntityId(relatedEntityId)
    }

    /**
     * 임시 파일을 정리합니다.
     * (스케줄러에서 주기적으로 호출)
     *
     * @param olderThan 이 시간보다 오래된 파일 삭제
     */
    @Transactional
    suspend fun cleanupTemporaryFiles(olderThan: ZonedDateTime) {
        log.info { "임시 파일 정리 시작: olderThan=$olderThan" }

        val temporaryFiles = fileRepository.findTemporaryFiles(olderThan)
        var deletedCount = 0

        for (file in temporaryFiles) {
            try {
                // 스토리지에서 파일 삭제
                fileStorageProvider.delete(file.storedFileName)

                // DB에서 파일 정보 삭제
                fileRepository.delete(file.id)

                deletedCount++
            } catch (e: Exception) {
                log.error(e) { "임시 파일 삭제 실패: fileId=${file.id}" }
            }
        }

        log.info { "임시 파일 정리 완료: deletedCount=$deletedCount" }
    }

    /**
     * 파일 확장자를 추출합니다.
     */
    private fun getFileExtension(filename: String): String {
        return filename.substringAfterLast('.', "").lowercase()
    }

    /**
     * 저장용 파일명을 생성합니다.
     */
    private fun generateStoredFileName(extension: String): String {
        return "${UUID.randomUUID()}.$extension"
    }

    /**
     * 이미지 파일 여부를 확인합니다.
     */
    private fun isImageFile(extension: String): Boolean {
        return extension in ALLOWED_IMAGE_EXTENSIONS
    }

    /**
     * 파일 접근 권한을 확인합니다.
     */
    private fun canAccess(fileInfo: FileInfo, requesterId: UUID): Boolean {
        // 업로더 본인이거나 관리자인 경우 접근 가능
        return fileInfo.uploaderId == requesterId || isAdmin(requesterId)
    }

    /**
     * 파일 삭제 권한을 확인합니다.
     */
    private fun canDelete(fileInfo: FileInfo, deleterId: UUID): Boolean {
        // 업로더 본인이거나 관리자인 경우 삭제 가능
        return fileInfo.uploaderId == deleterId || isAdmin(deleterId)
    }

    /**
     * 관리자 권한 확인 (실제로는 UserService 호출)
     */
    private fun isAdmin(userId: UUID): Boolean {
        // TODO: 실제 권한 확인 로직 구현
        return false
    }
}

/**
 * 파일 정보 모델
 */
data class FileInfo(
    val id: UUID,
    val originalFileName: String,
    val storedFileName: String,
    val fileSize: Long,
    val contentType: String,
    val extension: String,
    val category: FileCategory,
    val storageUrl: String,
    val thumbnailUrl: String?,
    val uploaderId: UUID,
    val relatedEntityId: UUID?,
    var status: FileStatus,
    val createdAt: ZonedDateTime,
    var updatedAt: ZonedDateTime,
    var deletedAt: ZonedDateTime? = null,
    var deletedBy: UUID? = null
)

/**
 * 파일 카테고리
 */
enum class FileCategory {
    ORDER_DOCUMENT,     // 주문서
    DELIVERY_RECEIPT,   // 인수증
    INVOICE,            // 계산서
    PROFILE_IMAGE,      // 프로필 이미지
    VEHICLE_IMAGE,      // 차량 이미지
    LICENSE,            // 면허증
    REGISTRATION,       // 등록증
    OTHER               // 기타
}

/**
 * 파일 상태
 */
enum class FileStatus {
    ACTIVE,             // 활성
    TEMPORARY,          // 임시 (업로드 후 미사용)
    DELETED             // 삭제됨
}

/**
 * 파일 예외
 */
class FileNotFoundException(message: String) : RuntimeException(message)
class FileAccessDeniedException(message: String) : RuntimeException(message)
class InvalidFileException(message: String) : RuntimeException(message)

/**
 * 파일 스토리지 프로바이더 인터페이스
 */
interface FileStorageProvider {
    suspend fun store(file: MultipartFile, storedFileName: String, category: FileCategory): String
    suspend fun delete(storedFileName: String)
    suspend fun getDownloadUrl(storedFileName: String): String
}

/**
 * 파일 검증기 인터페이스
 */
interface FileValidator {
    suspend fun validate(file: MultipartFile)
}

/**
 * 썸네일 생성기 인터페이스
 */
interface ThumbnailGenerator {
    suspend fun generate(file: MultipartFile, storedFileName: String): String
}
