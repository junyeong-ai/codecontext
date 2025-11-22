package sirius.appius.infra.messaging

import io.github.oshai.kotlinlogging.KotlinLogging
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.apache.kafka.clients.consumer.ConsumerRecord
import org.springframework.kafka.annotation.KafkaListener
import org.springframework.kafka.support.Acknowledgment
import org.springframework.stereotype.Component
import java.time.Duration
import java.util.UUID

/**
 * Kafka 메시지 컨슈머
 *
 * 다양한 도메인 이벤트를 수신하여 처리합니다.
 *
 * 토픽:
 * - tms-event-user: 유저 CUD 이벤트
 * - tms-auto-dispatch-api: 자동 배차 이벤트
 * - tms-event-order: 주문 이벤트
 * - tms-event-settlement: 정산 이벤트
 *
 * @author Infrastructure Team
 * @since 2024-01-01
 */
@Component
class KafkaConsumer(
    private val userEventHandler: UserEventHandler,
    private val autoDispatchEventHandler: AutoDispatchEventHandler,
    private val orderEventHandler: OrderEventHandler,
    private val settlementEventHandler: SettlementEventHandler,
    private val deadLetterQueue: DeadLetterQueue
) {
    private val log = KotlinLogging.logger {}
    private val coroutineScope = CoroutineScope(Dispatchers.IO)

    companion object {
        // 재시도 설정
        private const val MAX_RETRY_ATTEMPTS = 3
        private val RETRY_DELAY = Duration.ofSeconds(5)

        // 타임아웃 설정
        private val PROCESSING_TIMEOUT = Duration.ofSeconds(30)
    }

    /**
     * 유저 이벤트 컨슈머
     *
     * Topic: tms-event-user
     * GroupId: user-service-group
     */
    @KafkaListener(
        topics = ["tms-event-user"],
        groupId = "user-service-group",
        containerFactory = "kafkaListenerContainerFactory"
    )
    fun consumeUserEvent(
        record: ConsumerRecord<String, String>,
        acknowledgment: Acknowledgment
    ) {
        log.info { "유저 이벤트 수신: key=${record.key()}, partition=${record.partition()}, offset=${record.offset()}" }

        coroutineScope.launch {
            try {
                val event = parseUserEvent(record.value())
                userEventHandler.handle(event)

                // 수동 커밋
                acknowledgment.acknowledge()

                log.info { "유저 이벤트 처리 완료: userId=${event.userId}" }
            } catch (e: Exception) {
                handleError(record, e, acknowledgment)
            }
        }
    }

    /**
     * 자동 배차 이벤트 컨슈머
     *
     * Topic: tms-auto-dispatch-api
     * GroupId: auto-dispatch-group
     */
    @KafkaListener(
        topics = ["tms-auto-dispatch-api"],
        groupId = "auto-dispatch-group",
        containerFactory = "kafkaListenerContainerFactory"
    )
    fun consumeAutoDispatchEvent(
        record: ConsumerRecord<String, String>,
        acknowledgment: Acknowledgment
    ) {
        log.info { "자동 배차 이벤트 수신: key=${record.key()}" }

        coroutineScope.launch {
            try {
                val event = parseAutoDispatchEvent(record.value())
                autoDispatchEventHandler.handle(event)

                acknowledgment.acknowledge()

                log.info { "자동 배차 이벤트 처리 완료: orderId=${event.orderId}" }
            } catch (e: Exception) {
                handleError(record, e, acknowledgment)
            }
        }
    }

    /**
     * 주문 이벤트 컨슈머
     *
     * Topic: tms-event-order
     * GroupId: order-service-group
     */
    @KafkaListener(
        topics = ["tms-event-order"],
        groupId = "order-service-group",
        containerFactory = "kafkaListenerContainerFactory",
        concurrency = "3"  // 병렬 처리
    )
    fun consumeOrderEvent(
        record: ConsumerRecord<String, String>,
        acknowledgment: Acknowledgment
    ) {
        log.info { "주문 이벤트 수신: key=${record.key()}" }

        coroutineScope.launch {
            try {
                val event = parseOrderEvent(record.value())
                orderEventHandler.handle(event)

                acknowledgment.acknowledge()

                log.info { "주문 이벤트 처리 완료: orderId=${event.orderId}, status=${event.status}" }
            } catch (e: Exception) {
                handleError(record, e, acknowledgment)
            }
        }
    }

    /**
     * 정산 이벤트 컨슈머
     *
     * Topic: tms-event-settlement
     * GroupId: settlement-service-group
     */
    @KafkaListener(
        topics = ["tms-event-settlement"],
        groupId = "settlement-service-group",
        containerFactory = "kafkaListenerContainerFactory"
    )
    fun consumeSettlementEvent(
        record: ConsumerRecord<String, String>,
        acknowledgment: Acknowledgment
    ) {
        log.info { "정산 이벤트 수신: key=${record.key()}" }

        coroutineScope.launch {
            try {
                val event = parseSettlementEvent(record.value())
                settlementEventHandler.handle(event)

                acknowledgment.acknowledge()

                log.info { "정산 이벤트 처리 완료: settlementId=${event.settlementId}" }
            } catch (e: Exception) {
                handleError(record, e, acknowledgment)
            }
        }
    }

    /**
     * 에러 처리
     *
     * 재시도 로직과 DLQ 전송을 수행합니다.
     */
    private suspend fun handleError(
        record: ConsumerRecord<String, String>,
        exception: Exception,
        acknowledgment: Acknowledgment
    ) {
        log.error(exception) { "메시지 처리 실패: topic=${record.topic()}, key=${record.key()}" }

        // 재시도 횟수 확인
        val retryCount = getRetryCount(record)

        if (retryCount < MAX_RETRY_ATTEMPTS) {
            log.warn { "메시지 재시도 예정: retryCount=$retryCount" }
            // 재시도는 Kafka의 retry topic을 통해 처리
            // acknowledgment.nack()를 호출하지 않고 예외를 던져 컨테이너가 처리하도록 함
            throw exception
        } else {
            log.error { "최대 재시도 횟수 초과, DLQ로 전송: key=${record.key()}" }

            // Dead Letter Queue로 전송
            deadLetterQueue.send(
                topic = record.topic(),
                key = record.key(),
                value = record.value(),
                exception = exception
            )

            // 메시지 커밋 (더 이상 재시도하지 않음)
            acknowledgment.acknowledge()
        }
    }

    /**
     * 재시도 횟수 조회
     */
    private fun getRetryCount(record: ConsumerRecord<String, String>): Int {
        // 헤더에서 재시도 횟수 추출
        return record.headers()
            .lastHeader("retry-count")
            ?.value()
            ?.let { String(it).toIntOrNull() }
            ?: 0
    }

    /**
     * 유저 이벤트 파싱
     */
    private fun parseUserEvent(json: String): UserEvent {
        // JSON 파싱 로직
        return UserEvent(
            userId = UUID.randomUUID(),
            eventType = UserEventType.CREATED,
            userName = "test",
            email = "test@example.com"
        )
    }

    /**
     * 자동 배차 이벤트 파싱
     */
    private fun parseAutoDispatchEvent(json: String): AutoDispatchEvent {
        return AutoDispatchEvent(
            orderId = UUID.randomUUID(),
            driverId = UUID.randomUUID(),
            status = DispatchStatus.ASSIGNED
        )
    }

    /**
     * 주문 이벤트 파싱
     */
    private fun parseOrderEvent(json: String): OrderEvent {
        return OrderEvent(
            orderId = UUID.randomUUID(),
            orderNo = "ORD-001",
            status = OrderStatus.COMPLETED
        )
    }

    /**
     * 정산 이벤트 파싱
     */
    private fun parseSettlementEvent(json: String): SettlementEvent {
        return SettlementEvent(
            settlementId = UUID.randomUUID(),
            orderId = UUID.randomUUID(),
            status = SettlementStatus.APPROVED
        )
    }
}

// 이벤트 모델
data class UserEvent(
    val userId: UUID,
    val eventType: UserEventType,
    val userName: String,
    val email: String
)

data class AutoDispatchEvent(
    val orderId: UUID,
    val driverId: UUID,
    val status: DispatchStatus
)

data class OrderEvent(
    val orderId: UUID,
    val orderNo: String,
    val status: OrderStatus
)

data class SettlementEvent(
    val settlementId: UUID,
    val orderId: UUID,
    val status: SettlementStatus
)

// Enum 타입
enum class UserEventType { CREATED, UPDATED, DELETED }
enum class DispatchStatus { ASSIGNED, ACCEPTED, REJECTED }
enum class OrderStatus { PENDING, ASSIGNED, IN_PROGRESS, COMPLETED, CANCELLED }
enum class SettlementStatus { PENDING, APPROVED, REJECTED, COMPLETED }

// 이벤트 핸들러 인터페이스
interface UserEventHandler {
    suspend fun handle(event: UserEvent)
}

interface AutoDispatchEventHandler {
    suspend fun handle(event: AutoDispatchEvent)
}

interface OrderEventHandler {
    suspend fun handle(event: OrderEvent)
}

interface SettlementEventHandler {
    suspend fun handle(event: SettlementEvent)
}

// Dead Letter Queue
interface DeadLetterQueue {
    suspend fun send(topic: String, key: String, value: String, exception: Exception)
}
