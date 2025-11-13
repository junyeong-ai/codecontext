package sirius.appius.infra.config

import com.fasterxml.jackson.databind.ObjectMapper
import io.lettuce.core.ClientOptions
import io.lettuce.core.SocketOptions
import org.springframework.boot.autoconfigure.data.redis.RedisProperties
import org.springframework.cache.CacheManager
import org.springframework.cache.annotation.EnableCaching
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.context.annotation.Primary
import org.springframework.data.redis.cache.RedisCacheConfiguration
import org.springframework.data.redis.cache.RedisCacheManager
import org.springframework.data.redis.connection.RedisConnectionFactory
import org.springframework.data.redis.connection.lettuce.LettuceClientConfiguration
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory
import org.springframework.data.redis.core.RedisTemplate
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer
import org.springframework.data.redis.serializer.RedisSerializationContext
import org.springframework.data.redis.serializer.StringRedisSerializer
import java.time.Duration

/**
 * Redis 캐시 설정
 *
 * Spring Cache Abstraction과 Redis를 통합하여
 * 분산 캐시 환경을 구성합니다.
 *
 * 주요 기능:
 * - Redis 연결 설정
 * - 캐시 매니저 설정
 * - RedisTemplate 설정
 * - 캐시별 TTL 설정
 *
 * @author Infrastructure Team
 * @since 2024-01-01
 */
@Configuration
@EnableCaching
class CacheConfig(
    private val redisProperties: RedisProperties,
    private val objectMapper: ObjectMapper
) {

    companion object {
        // 캐시 이름 정의
        const val DASHBOARD_CACHE = "dashboard"
        const val USER_CACHE = "users"
        const val ORDER_CACHE = "orders"
        const val DRIVER_CACHE = "drivers"
        const val ORGANIZATION_CACHE = "organizations"

        // 기본 TTL
        private val DEFAULT_TTL = Duration.ofMinutes(10)

        // 캐시별 TTL
        private val CACHE_TTL_MAP = mapOf(
            DASHBOARD_CACHE to Duration.ofMinutes(10),
            USER_CACHE to Duration.ofHours(1),
            ORDER_CACHE to Duration.ofMinutes(5),
            DRIVER_CACHE to Duration.ofHours(1),
            ORGANIZATION_CACHE to Duration.ofHours(2)
        )
    }

    /**
     * Redis 연결 팩토리 설정
     *
     * Lettuce 클라이언트를 사용하여 비동기/논블로킹 연결을 구성합니다.
     */
    @Bean
    @Primary
    fun redisConnectionFactory(): RedisConnectionFactory {
        val socketOptions = SocketOptions.builder()
            .connectTimeout(Duration.ofSeconds(10))
            .keepAlive(true)
            .build()

        val clientOptions = ClientOptions.builder()
            .socketOptions(socketOptions)
            .autoReconnect(true)
            .build()

        val clientConfig = LettuceClientConfiguration.builder()
            .clientOptions(clientOptions)
            .commandTimeout(Duration.ofSeconds(5))
            .build()

        val factory = LettuceConnectionFactory(
            redisProperties.host,
            redisProperties.port,
            clientConfig
        )

        // Redis 비밀번호 설정
        redisProperties.password?.let {
            factory.setPassword(it)
        }

        factory.afterPropertiesSet()
        return factory
    }

    /**
     * Redis 캐시 매니저 설정
     *
     * 캐시별로 다른 TTL과 직렬화 설정을 적용합니다.
     */
    @Bean
    @Primary
    fun cacheManager(
        redisConnectionFactory: RedisConnectionFactory
    ): CacheManager {
        // 기본 캐시 설정
        val defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(DEFAULT_TTL)
            .disableCachingNullValues()
            .serializeKeysWith(
                RedisSerializationContext.SerializationPair.fromSerializer(
                    StringRedisSerializer()
                )
            )
            .serializeValuesWith(
                RedisSerializationContext.SerializationPair.fromSerializer(
                    GenericJackson2JsonRedisSerializer(objectMapper)
                )
            )

        // 캐시별 개별 설정
        val cacheConfigurations = CACHE_TTL_MAP.mapValues { (_, ttl) ->
            defaultConfig.entryTtl(ttl)
        }

        return RedisCacheManager.builder(redisConnectionFactory)
            .cacheDefaults(defaultConfig)
            .withInitialCacheConfigurations(cacheConfigurations)
            .transactionAware()
            .build()
    }

    /**
     * RedisTemplate 설정
     *
     * 캐시 외에 Redis를 직접 사용할 때 필요한 템플릿입니다.
     */
    @Bean
    fun redisTemplate(
        redisConnectionFactory: RedisConnectionFactory
    ): RedisTemplate<String, Any> {
        val template = RedisTemplate<String, Any>()
        template.connectionFactory = redisConnectionFactory

        // Key 직렬화: String
        val stringSerializer = StringRedisSerializer()
        template.keySerializer = stringSerializer
        template.hashKeySerializer = stringSerializer

        // Value 직렬화: JSON
        val jsonSerializer = GenericJackson2JsonRedisSerializer(objectMapper)
        template.valueSerializer = jsonSerializer
        template.hashValueSerializer = jsonSerializer

        template.afterPropertiesSet()
        return template
    }

    /**
     * String 전용 RedisTemplate 설정
     *
     * 간단한 String 값을 저장할 때 사용합니다.
     */
    @Bean
    fun stringRedisTemplate(
        redisConnectionFactory: RedisConnectionFactory
    ): RedisTemplate<String, String> {
        val template = RedisTemplate<String, String>()
        template.connectionFactory = redisConnectionFactory

        val stringSerializer = StringRedisSerializer()
        template.keySerializer = stringSerializer
        template.valueSerializer = stringSerializer
        template.hashKeySerializer = stringSerializer
        template.hashValueSerializer = stringSerializer

        template.afterPropertiesSet()
        return template
    }
}

/**
 * 캐시 키 생성 유틸리티
 *
 * 일관된 캐시 키 포맷을 유지합니다.
 */
object CacheKeyGenerator {

    /**
     * 대시보드 캐시 키 생성
     *
     * Format: dashboard:{orgId}:{apiName}
     */
    fun dashboardKey(orgId: String, apiName: String): String {
        return "dashboard:$orgId:$apiName"
    }

    /**
     * 사용자 캐시 키 생성
     *
     * Format: users:{userId}
     */
    fun userKey(userId: String): String {
        return "users:$userId"
    }

    /**
     * 주문 캐시 키 생성
     *
     * Format: orders:{orderId}
     */
    fun orderKey(orderId: String): String {
        return "orders:$orderId"
    }

    /**
     * 기사 캐시 키 생성
     *
     * Format: drivers:{driverId}
     */
    fun driverKey(driverId: String): String {
        return "drivers:$driverId"
    }

    /**
     * 조직 캐시 키 생성
     *
     * Format: organizations:{organizationId}
     */
    fun organizationKey(organizationId: String): String {
        return "organizations:$organizationId"
    }

    /**
     * 패턴 기반 키 생성
     *
     * Format: {prefix}:{id}
     */
    fun generateKey(prefix: String, id: String): String {
        return "$prefix:$id"
    }

    /**
     * 복합 키 생성
     *
     * Format: {prefix}:{id1}:{id2}:...
     */
    fun generateCompositeKey(prefix: String, vararg ids: String): String {
        return "$prefix:${ids.joinToString(":")}"
    }
}

/**
 * 캐시 이벤트 리스너
 *
 * 도메인 변경 이벤트를 수신하여 관련 캐시를 무효화합니다.
 */
@Component
class CacheInvalidationListener(
    private val cacheManager: CacheManager
) {

    private val log = io.github.oshai.kotlinlogging.KotlinLogging.logger {}

    /**
     * 정산 CUD 이벤트 수신 시 대시보드 캐시 무효화
     */
    @EventListener
    fun onSettlementChanged(event: SettlementChangedEvent) {
        log.info { "Settlement changed, invalidating dashboard cache: orgId=${event.organizationId}" }
        invalidateDashboardCache(event.organizationId)
    }

    /**
     * 주문 CUD 이벤트 수신 시 대시보드 캐시 무효화
     */
    @EventListener
    fun onOrderChanged(event: OrderChangedEvent) {
        log.info { "Order changed, invalidating dashboard cache: orgId=${event.organizationId}" }
        invalidateDashboardCache(event.organizationId)
    }

    /**
     * 사용자 알림 CUD 이벤트 수신 시 사용자 캐시 무효화
     */
    @EventListener
    fun onUserAlertChanged(event: UserAlertChangedEvent) {
        log.info { "User alert changed, invalidating user cache: userId=${event.userId}" }
        invalidateUserCache(event.userId)
    }

    /**
     * 대시보드 캐시 무효화
     */
    private fun invalidateDashboardCache(organizationId: String) {
        cacheManager.getCache(CacheConfig.DASHBOARD_CACHE)?.let { cache ->
            // 조직 ID로 시작하는 모든 키 제거
            // Note: Redis에서는 패턴 매칭을 위해 별도 구현 필요
            cache.clear()
        }
    }

    /**
     * 사용자 캐시 무효화
     */
    private fun invalidateUserCache(userId: String) {
        cacheManager.getCache(CacheConfig.USER_CACHE)?.let { cache ->
            cache.evict(CacheKeyGenerator.userKey(userId))
        }
    }
}

// 도메인 이벤트 클래스들
data class SettlementChangedEvent(val organizationId: String)
data class OrderChangedEvent(val organizationId: String)
data class UserAlertChangedEvent(val userId: String)
