package sirius.appius.modules.settlement.service

import org.springframework.data.r2dbc.repository.Query
import org.springframework.data.repository.kotlin.CoroutineCrudRepository
import org.springframework.stereotype.Repository
import java.time.ZonedDateTime
import java.util.UUID

/**
 * 정산 데이터 저장소 인터페이스
 *
 * R2DBC를 사용한 비동기 정산 데이터 접근 계층
 *
 * @author Settlement Team
 * @since 2024-01-01
 */
@Repository
interface PaymentRepository : CoroutineCrudRepository<Settlement, UUID> {

    /**
     * 주문 ID로 정산 데이터를 조회합니다.
     *
     * @param orderId 주문 ID
     * @return 정산 데이터 (없으면 null)
     */
    @Query(
        """
        SELECT * FROM settlements
        WHERE order_id = :orderId
        LIMIT 1
        """
    )
    suspend fun findByOrderId(orderId: UUID): Settlement?

    /**
     * 차주(기사) ID로 정산 목록을 조회합니다.
     *
     * @param driverId 차주 ID
     * @return 정산 목록
     */
    @Query(
        """
        SELECT * FROM settlements
        WHERE driver_id = :driverId
        ORDER BY created_at DESC
        """
    )
    suspend fun findByDriverId(driverId: UUID): List<Settlement>

    /**
     * 화주 ID로 정산 목록을 조회합니다.
     *
     * @param shipperId 화주 ID
     * @return 정산 목록
     */
    @Query(
        """
        SELECT * FROM settlements
        WHERE shipper_id = :shipperId
        ORDER BY created_at DESC
        """
    )
    suspend fun findByShipperId(shipperId: UUID): List<Settlement>

    /**
     * 특정 기간과 상태로 정산 목록을 조회합니다.
     *
     * @param startDate 시작일
     * @param endDate 종료일
     * @param status 정산 상태 (선택)
     * @return 정산 목록
     */
    @Query(
        """
        SELECT * FROM settlements
        WHERE created_at >= :startDate
        AND created_at <= :endDate
        AND (:status IS NULL OR status = :status)
        ORDER BY created_at DESC
        """
    )
    suspend fun findByPeriod(
        startDate: ZonedDateTime,
        endDate: ZonedDateTime,
        status: SettlementStatus?
    ): List<Settlement>

    /**
     * 정산 상태별 개수를 조회합니다.
     *
     * @param status 정산 상태
     * @return 개수
     */
    @Query(
        """
        SELECT COUNT(*) FROM settlements
        WHERE status = :status
        """
    )
    suspend fun countByStatus(status: SettlementStatus): Long

    /**
     * 대기 중인 정산 목록을 조회합니다.
     *
     * @return 대기 중인 정산 목록
     */
    @Query(
        """
        SELECT * FROM settlements
        WHERE status = 'PENDING'
        ORDER BY created_at ASC
        """
    )
    suspend fun findPendingSettlements(): List<Settlement>

    /**
     * 특정 기간의 승인된 정산 목록을 조회합니다.
     * (정산 리포트 생성 시 사용)
     *
     * @param startDate 시작일
     * @param endDate 종료일
     * @return 승인된 정산 목록
     */
    @Query(
        """
        SELECT * FROM settlements
        WHERE status = 'APPROVED'
        AND approved_at >= :startDate
        AND approved_at <= :endDate
        ORDER BY approved_at DESC
        """
    )
    suspend fun findApprovedSettlementsByPeriod(
        startDate: ZonedDateTime,
        endDate: ZonedDateTime
    ): List<Settlement>

    /**
     * 정산 데이터를 업데이트합니다.
     *
     * @param settlement 업데이트할 정산 데이터
     * @return 업데이트된 정산 데이터
     */
    suspend fun update(settlement: Settlement): Settlement {
        return save(settlement)
    }
}

/**
 * 정산 통계 데이터 DTO
 */
data class SettlementStatistics(
    val totalCount: Long,
    val pendingCount: Long,
    val approvedCount: Long,
    val rejectedCount: Long,
    val completedCount: Long
)

/**
 * 정산 집계 데이터 저장소 확장 인터페이스
 *
 * 복잡한 집계 쿼리를 위한 커스텀 메서드 정의
 */
@Repository
interface PaymentRepositoryCustom {

    /**
     * 특정 기간의 정산 통계를 조회합니다.
     *
     * @param startDate 시작일
     * @param endDate 종료일
     * @return 정산 통계
     */
    suspend fun getStatistics(
        startDate: ZonedDateTime,
        endDate: ZonedDateTime
    ): SettlementStatistics

    /**
     * 차주별 정산 합계를 조회합니다.
     *
     * @param driverId 차주 ID
     * @param startDate 시작일
     * @param endDate 종료일
     * @return 정산 합계 금액
     */
    suspend fun sumDriverAmountByPeriod(
        driverId: UUID,
        startDate: ZonedDateTime,
        endDate: ZonedDateTime
    ): java.math.BigDecimal
}
