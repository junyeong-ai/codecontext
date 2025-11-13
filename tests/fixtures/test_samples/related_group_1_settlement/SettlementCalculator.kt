package sirius.appius.modules.settlement.service

import io.github.oshai.kotlinlogging.KotlinLogging
import org.springframework.stereotype.Component
import java.math.BigDecimal
import java.math.RoundingMode
import java.util.UUID

/**
 * 정산 금액 계산기
 *
 * 주요 책임:
 * - 차주(기사) 지급액 계산
 * - 화주 청구액 계산
 * - 플랫폼 수수료 계산
 * - 부가세 계산
 *
 * 계산 규칙:
 * - 차주 지급액 = (기본 운임 + 추가 비용) * (1 - 플랫폼 수수료율)
 * - 화주 청구액 = (기본 운임 + 추가 비용) * (1 + 부가세율)
 * - 플랫폼 수수료 = (기본 운임 + 추가 비용) * 플랫폼 수수료율
 *
 * @author Settlement Team
 * @since 2024-01-01
 */
@Component
class SettlementCalculator(
    private val settlementConfig: SettlementConfig,
    private val driverInfoService: DriverInfoService
) {
    private val log = KotlinLogging.logger {}

    companion object {
        // 소수점 처리 자릿수
        private const val SCALE = 2

        // 기본 플랫폼 수수료율 (15%)
        private val DEFAULT_PLATFORM_FEE_RATE = BigDecimal("0.15")

        // 부가세율 (10%)
        private val VAT_RATE = BigDecimal("0.10")
    }

    /**
     * 정산 금액을 계산합니다.
     *
     * @param baseAmount 기본 운임
     * @param extraFees 추가 비용
     * @param driverId 차주 ID
     * @param shipperId 화주 ID
     * @return 계산 결과
     */
    suspend fun calculate(
        baseAmount: BigDecimal,
        extraFees: BigDecimal,
        driverId: UUID,
        shipperId: UUID
    ): CalculationResult {
        log.debug { "정산 계산 시작: baseAmount=$baseAmount, extraFees=$extraFees" }

        // 총 운임 계산
        val totalAmount = baseAmount.add(extraFees)

        // 플랫폼 수수료율 조회 (기사 등급에 따라 다를 수 있음)
        val platformFeeRate = getPlatformFeeRate(driverId)

        // 플랫폼 수수료 계산
        val platformFee = totalAmount
            .multiply(platformFeeRate)
            .setScale(SCALE, RoundingMode.HALF_UP)

        // 차주 지급액 계산 (총 운임 - 플랫폼 수수료)
        val driverAmount = totalAmount
            .subtract(platformFee)
            .setScale(SCALE, RoundingMode.HALF_UP)

        // 부가세 계산
        val vat = totalAmount
            .multiply(VAT_RATE)
            .setScale(SCALE, RoundingMode.HALF_UP)

        // 화주 청구액 계산 (총 운임 + 부가세)
        val shipperAmount = totalAmount
            .add(vat)
            .setScale(SCALE, RoundingMode.HALF_UP)

        val result = CalculationResult(
            driverAmount = driverAmount,
            shipperAmount = shipperAmount,
            platformFee = platformFee,
            vat = vat,
            totalAmount = totalAmount
        )

        log.debug { "정산 계산 완료: $result" }
        return result
    }

    /**
     * 플랫폼 수수료율을 조회합니다.
     * 기사 등급(정회원/준회원)에 따라 수수료율이 다를 수 있습니다.
     *
     * @param driverId 차주 ID
     * @return 플랫폼 수수료율
     */
    private suspend fun getPlatformFeeRate(driverId: UUID): BigDecimal {
        val driverInfo = driverInfoService.getDriverInfo(driverId)

        return when (driverInfo.memberType) {
            DriverMemberType.FULL_MEMBER -> settlementConfig.fullMemberFeeRate
            DriverMemberType.ASSOCIATE_MEMBER -> settlementConfig.associateMemberFeeRate
            else -> DEFAULT_PLATFORM_FEE_RATE
        }
    }

    /**
     * 정산 금액 재계산 (수정 시 사용)
     *
     * @param settlement 기존 정산 데이터
     * @param newBaseAmount 새 기본 운임
     * @param newExtraFees 새 추가 비용
     * @return 재계산 결과
     */
    suspend fun recalculate(
        settlement: Settlement,
        newBaseAmount: BigDecimal,
        newExtraFees: BigDecimal
    ): CalculationResult {
        log.info { "정산 재계산: settlementId=${settlement.id}" }

        return calculate(
            baseAmount = newBaseAmount,
            extraFees = newExtraFees,
            driverId = settlement.driverId,
            shipperId = settlement.shipperId
        )
    }

    /**
     * 월별 정산 집계 계산
     *
     * @param settlements 정산 목록
     * @return 월별 집계 결과
     */
    fun aggregateMonthly(settlements: List<Settlement>): MonthlyAggregation {
        val totalDriverAmount = settlements.sumOf { it.driverAmount }
        val totalShipperAmount = settlements.sumOf { it.shipperAmount }
        val totalPlatformFee = settlements.sumOf { it.platformFee }

        return MonthlyAggregation(
            settlementCount = settlements.size,
            totalDriverAmount = totalDriverAmount,
            totalShipperAmount = totalShipperAmount,
            totalPlatformFee = totalPlatformFee,
            averageDriverAmount = if (settlements.isNotEmpty()) {
                totalDriverAmount.divide(
                    BigDecimal(settlements.size),
                    SCALE,
                    RoundingMode.HALF_UP
                )
            } else BigDecimal.ZERO
        )
    }
}

/**
 * 정산 계산 결과
 */
data class CalculationResult(
    val driverAmount: BigDecimal,      // 차주 지급액
    val shipperAmount: BigDecimal,     // 화주 청구액
    val platformFee: BigDecimal,       // 플랫폼 수수료
    val vat: BigDecimal,               // 부가세
    val totalAmount: BigDecimal        // 총 운임
)

/**
 * 월별 정산 집계 결과
 */
data class MonthlyAggregation(
    val settlementCount: Int,
    val totalDriverAmount: BigDecimal,
    val totalShipperAmount: BigDecimal,
    val totalPlatformFee: BigDecimal,
    val averageDriverAmount: BigDecimal
)

/**
 * 정산 설정
 */
@Component
data class SettlementConfig(
    val fullMemberFeeRate: BigDecimal = BigDecimal("0.12"),      // 정회원 수수료율 (12%)
    val associateMemberFeeRate: BigDecimal = BigDecimal("0.15")  // 준회원 수수료율 (15%)
)

/**
 * 기사 정보 서비스 (모의)
 */
@Component
class DriverInfoService {
    suspend fun getDriverInfo(driverId: UUID): DriverInfo {
        // 실제로는 Driver API를 호출하여 정보를 가져옵니다
        return DriverInfo(
            id = driverId,
            memberType = DriverMemberType.ASSOCIATE_MEMBER
        )
    }
}

/**
 * 기사 정보
 */
data class DriverInfo(
    val id: UUID,
    val memberType: DriverMemberType
)

/**
 * 기사 회원 타입
 */
enum class DriverMemberType {
    FULL_MEMBER,        // 정회원
    ASSOCIATE_MEMBER,   // 준회원
    TRIAL_MEMBER        // 체험 회원
}
