package sirius.appius.modules.settlement.service

import io.github.oshai.kotlinlogging.KotlinLogging
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.math.BigDecimal
import java.time.ZonedDateTime
import java.util.UUID

/**
 * 정산 서비스
 *
 * 주요 책임:
 * - 운송 완료된 주문에 대한 정산 데이터 생성 및 관리
 * - 차주(기사) 매입 금액 계산
 * - 화주 매출 금액 계산
 * - 정산 상태 변경 및 승인 처리
 *
 * @author Settlement Team
 * @since 2024-01-01
 */
@Service
class SettlementService(
    private val settlementRepository: PaymentRepository,
    private val settlementCalculator: SettlementCalculator,
    private val settlementEventPublisher: SettlementEventPublisher
) {
    private val log = KotlinLogging.logger {}

    /**
     * 주문 완료 시 정산 데이터를 생성합니다.
     *
     * @param orderId 주문 ID
     * @param driverId 차주(기사) ID
     * @param shipperId 화주 ID
     * @param baseAmount 기본 운임
     * @param extraFees 추가 비용 (톨게이트, 주차비 등)
     * @return 생성된 정산 ID
     */
    @Transactional
    suspend fun createSettlement(
        orderId: UUID,
        driverId: UUID,
        shipperId: UUID,
        baseAmount: BigDecimal,
        extraFees: BigDecimal
    ): UUID {
        log.info { "정산 생성 시작: orderId=$orderId, driverId=$driverId, shipperId=$shipperId" }

        // 기존 정산 데이터 확인
        val existingSettlement = settlementRepository.findByOrderId(orderId)
        if (existingSettlement != null) {
            log.warn { "이미 정산이 존재합니다: settlementId=${existingSettlement.id}" }
            return existingSettlement.id
        }

        // 정산 금액 계산
        val calculationResult = settlementCalculator.calculate(
            baseAmount = baseAmount,
            extraFees = extraFees,
            driverId = driverId,
            shipperId = shipperId
        )

        // 정산 데이터 저장
        val settlement = Settlement(
            id = UUID.randomUUID(),
            orderId = orderId,
            driverId = driverId,
            shipperId = shipperId,
            driverAmount = calculationResult.driverAmount,
            shipperAmount = calculationResult.shipperAmount,
            platformFee = calculationResult.platformFee,
            status = SettlementStatus.PENDING,
            createdAt = ZonedDateTime.now(),
            updatedAt = ZonedDateTime.now()
        )

        val savedSettlement = settlementRepository.save(settlement)

        // 정산 생성 이벤트 발행
        settlementEventPublisher.publishCreated(savedSettlement)

        log.info { "정산 생성 완료: settlementId=${savedSettlement.id}" }
        return savedSettlement.id
    }

    /**
     * 정산 상태를 변경합니다.
     *
     * @param settlementId 정산 ID
     * @param newStatus 변경할 상태
     */
    @Transactional
    suspend fun updateStatus(settlementId: UUID, newStatus: SettlementStatus) {
        log.info { "정산 상태 변경: settlementId=$settlementId, newStatus=$newStatus" }

        val settlement = settlementRepository.findById(settlementId)
            ?: throw SettlementNotFoundException("정산을 찾을 수 없습니다: $settlementId")

        // 상태 변경 가능 여부 검증
        if (!settlement.canTransitionTo(newStatus)) {
            throw IllegalStateTransitionException(
                "정산 상태를 ${settlement.status}에서 ${newStatus}로 변경할 수 없습니다"
            )
        }

        settlement.status = newStatus
        settlement.updatedAt = ZonedDateTime.now()

        settlementRepository.update(settlement)
        settlementEventPublisher.publishStatusChanged(settlement)

        log.info { "정산 상태 변경 완료: settlementId=$settlementId" }
    }

    /**
     * 정산을 승인합니다.
     *
     * @param settlementId 정산 ID
     * @param approvedBy 승인자 ID
     */
    @Transactional
    suspend fun approve(settlementId: UUID, approvedBy: UUID) {
        log.info { "정산 승인: settlementId=$settlementId, approvedBy=$approvedBy" }

        val settlement = settlementRepository.findById(settlementId)
            ?: throw SettlementNotFoundException("정산을 찾을 수 없습니다: $settlementId")

        if (settlement.status != SettlementStatus.PENDING) {
            throw IllegalStateException("대기 중인 정산만 승인할 수 있습니다")
        }

        settlement.status = SettlementStatus.APPROVED
        settlement.approvedBy = approvedBy
        settlement.approvedAt = ZonedDateTime.now()
        settlement.updatedAt = ZonedDateTime.now()

        settlementRepository.update(settlement)
        settlementEventPublisher.publishApproved(settlement)

        log.info { "정산 승인 완료: settlementId=$settlementId" }
    }

    /**
     * 특정 기간의 정산 목록을 조회합니다.
     *
     * @param startDate 시작일
     * @param endDate 종료일
     * @param status 정산 상태 (선택)
     * @return 정산 목록
     */
    suspend fun findSettlementsByPeriod(
        startDate: ZonedDateTime,
        endDate: ZonedDateTime,
        status: SettlementStatus? = null
    ): List<Settlement> {
        log.debug { "기간별 정산 조회: startDate=$startDate, endDate=$endDate, status=$status" }
        return settlementRepository.findByPeriod(startDate, endDate, status)
    }
}

/**
 * 정산 데이터 모델
 */
data class Settlement(
    val id: UUID,
    val orderId: UUID,
    val driverId: UUID,
    val shipperId: UUID,
    val driverAmount: BigDecimal,
    val shipperAmount: BigDecimal,
    val platformFee: BigDecimal,
    var status: SettlementStatus,
    val createdAt: ZonedDateTime,
    var updatedAt: ZonedDateTime,
    var approvedBy: UUID? = null,
    var approvedAt: ZonedDateTime? = null
) {
    fun canTransitionTo(newStatus: SettlementStatus): Boolean {
        return when (status) {
            SettlementStatus.PENDING -> newStatus in setOf(
                SettlementStatus.APPROVED,
                SettlementStatus.REJECTED
            )
            SettlementStatus.APPROVED -> newStatus == SettlementStatus.COMPLETED
            else -> false
        }
    }
}

/**
 * 정산 상태
 */
enum class SettlementStatus {
    PENDING,    // 대기
    APPROVED,   // 승인
    REJECTED,   // 거부
    COMPLETED   // 완료
}

/**
 * 정산 이벤트 퍼블리셔
 */
interface SettlementEventPublisher {
    suspend fun publishCreated(settlement: Settlement)
    suspend fun publishStatusChanged(settlement: Settlement)
    suspend fun publishApproved(settlement: Settlement)
}

/**
 * 정산 예외
 */
class SettlementNotFoundException(message: String) : RuntimeException(message)
class IllegalStateTransitionException(message: String) : RuntimeException(message)
