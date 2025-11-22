package sirius.appius.infra.search

import co.elastic.clients.elasticsearch.ElasticsearchClient
import co.elastic.clients.elasticsearch._types.query_dsl.Query
import co.elastic.clients.elasticsearch.core.*
import co.elastic.clients.elasticsearch.core.search.Hit
import co.elastic.clients.elasticsearch.indices.CreateIndexRequest
import co.elastic.clients.elasticsearch.indices.DeleteIndexRequest
import co.elastic.clients.elasticsearch.indices.ExistsRequest
import io.github.oshai.kotlinlogging.KotlinLogging
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.springframework.stereotype.Component
import java.time.ZonedDateTime

/**
 * Elasticsearch 템플릿
 *
 * Elasticsearch 클라이언트를 래핑하여 편리한 검색 API를 제공합니다.
 *
 * 주요 기능:
 * - 문서 인덱싱
 * - 전문 검색
 * - 집계 쿼리
 * - 인덱스 관리
 *
 * @author Infrastructure Team
 * @since 2024-01-01
 */
@Component
class ElasticTemplate(
    private val elasticsearchClient: ElasticsearchClient
) {
    private val log = KotlinLogging.logger {}

    companion object {
        // 인덱스 이름
        const val ORDER_INDEX = "orders"
        const val SETTLEMENT_INDEX = "settlements"
        const val DRIVER_INDEX = "drivers"
        const val ORGANIZATION_INDEX = "organizations"

        // 기본 설정
        private const val DEFAULT_SIZE = 20
        private const val MAX_SIZE = 1000
    }

    /**
     * 문서를 인덱싱합니다.
     *
     * @param index 인덱스 이름
     * @param id 문서 ID
     * @param document 문서 객체
     * @return 인덱싱 결과
     */
    suspend fun <T> index(
        index: String,
        id: String,
        document: T
    ): IndexResponse = withContext(Dispatchers.IO) {
        log.debug { "문서 인덱싱: index=$index, id=$id" }

        val response = elasticsearchClient.index { req ->
            req.index(index)
                .id(id)
                .document(document)
        }

        log.info { "문서 인덱싱 완료: index=$index, id=$id, result=${response.result()}" }
        response
    }

    /**
     * 문서를 조회합니다.
     *
     * @param index 인덱스 이름
     * @param id 문서 ID
     * @param clazz 문서 클래스
     * @return 문서 객체 (없으면 null)
     */
    suspend fun <T> get(
        index: String,
        id: String,
        clazz: Class<T>
    ): T? = withContext(Dispatchers.IO) {
        log.debug { "문서 조회: index=$index, id=$id" }

        try {
            val response = elasticsearchClient.get(
                { req -> req.index(index).id(id) },
                clazz
            )

            if (response.found()) {
                log.info { "문서 조회 완료: index=$index, id=$id" }
                response.source()
            } else {
                log.warn { "문서를 찾을 수 없음: index=$index, id=$id" }
                null
            }
        } catch (e: Exception) {
            log.error(e) { "문서 조회 실패: index=$index, id=$id" }
            null
        }
    }

    /**
     * 문서를 삭제합니다.
     *
     * @param index 인덱스 이름
     * @param id 문서 ID
     * @return 삭제 결과
     */
    suspend fun delete(
        index: String,
        id: String
    ): DeleteResponse = withContext(Dispatchers.IO) {
        log.debug { "문서 삭제: index=$index, id=$id" }

        val response = elasticsearchClient.delete { req ->
            req.index(index).id(id)
        }

        log.info { "문서 삭제 완료: index=$index, id=$id, result=${response.result()}" }
        response
    }

    /**
     * 검색을 수행합니다.
     *
     * @param index 인덱스 이름
     * @param query 검색 쿼리
     * @param clazz 문서 클래스
     * @param from 시작 위치
     * @param size 조회 개수
     * @return 검색 결과 리스트
     */
    suspend fun <T> search(
        index: String,
        query: Query,
        clazz: Class<T>,
        from: Int = 0,
        size: Int = DEFAULT_SIZE
    ): SearchResult<T> = withContext(Dispatchers.IO) {
        log.debug { "검색 수행: index=$index, from=$from, size=$size" }

        val response = elasticsearchClient.search(
            { req ->
                req.index(index)
                    .query(query)
                    .from(from)
                    .size(size.coerceAtMost(MAX_SIZE))
            },
            clazz
        )

        val hits = response.hits().hits().map { hit ->
            SearchHit(
                id = hit.id(),
                score = hit.score() ?: 0.0,
                source = hit.source()!!
            )
        }

        val total = response.hits().total()?.value() ?: 0

        log.info { "검색 완료: index=$index, total=$total, returned=${hits.size}" }

        SearchResult(
            hits = hits,
            total = total,
            took = response.took()
        )
    }

    /**
     * 전문 검색을 수행합니다.
     *
     * @param index 인덱스 이름
     * @param field 검색 필드
     * @param text 검색 텍스트
     * @param clazz 문서 클래스
     * @return 검색 결과
     */
    suspend fun <T> fullTextSearch(
        index: String,
        field: String,
        text: String,
        clazz: Class<T>,
        from: Int = 0,
        size: Int = DEFAULT_SIZE
    ): SearchResult<T> {
        log.debug { "전문 검색: index=$index, field=$field, text=$text" }

        val query = Query.of { q ->
            q.match { m ->
                m.field(field)
                    .query { v -> v.stringValue(text) }
            }
        }

        return search(index, query, clazz, from, size)
    }

    /**
     * 다중 필드 검색을 수행합니다.
     *
     * @param index 인덱스 이름
     * @param fields 검색 필드 목록
     * @param text 검색 텍스트
     * @param clazz 문서 클래스
     * @return 검색 결과
     */
    suspend fun <T> multiFieldSearch(
        index: String,
        fields: List<String>,
        text: String,
        clazz: Class<T>,
        from: Int = 0,
        size: Int = DEFAULT_SIZE
    ): SearchResult<T> {
        log.debug { "다중 필드 검색: index=$index, fields=$fields, text=$text" }

        val query = Query.of { q ->
            q.multiMatch { m ->
                m.fields(fields)
                    .query(text)
            }
        }

        return search(index, query, clazz, from, size)
    }

    /**
     * 범위 검색을 수행합니다.
     *
     * @param index 인덱스 이름
     * @param field 필드명
     * @param from 시작 값
     * @param to 종료 값
     * @param clazz 문서 클래스
     * @return 검색 결과
     */
    suspend fun <T> rangeSearch(
        index: String,
        field: String,
        from: Any?,
        to: Any?,
        clazz: Class<T>
    ): SearchResult<T> {
        log.debug { "범위 검색: index=$index, field=$field, from=$from, to=$to" }

        val query = Query.of { q ->
            q.range { r ->
                r.field(field).apply {
                    from?.let { gte(it.toString()) }
                    to?.let { lte(it.toString()) }
                }
            }
        }

        return search(index, query, clazz)
    }

    /**
     * 인덱스가 존재하는지 확인합니다.
     *
     * @param index 인덱스 이름
     * @return 존재 여부
     */
    suspend fun existsIndex(index: String): Boolean = withContext(Dispatchers.IO) {
        log.debug { "인덱스 존재 확인: index=$index" }

        val response = elasticsearchClient.indices().exists { req ->
            req.index(index)
        }

        response.value()
    }

    /**
     * 인덱스를 생성합니다.
     *
     * @param index 인덱스 이름
     * @param mappings 매핑 설정 (JSON)
     * @param settings 인덱스 설정 (JSON)
     */
    suspend fun createIndex(
        index: String,
        mappings: String? = null,
        settings: String? = null
    ): Boolean = withContext(Dispatchers.IO) {
        log.info { "인덱스 생성: index=$index" }

        try {
            elasticsearchClient.indices().create { req ->
                req.index(index).apply {
                    mappings?.let { /* 매핑 설정 */ }
                    settings?.let { /* 인덱스 설정 */ }
                }
            }

            log.info { "인덱스 생성 완료: index=$index" }
            true
        } catch (e: Exception) {
            log.error(e) { "인덱스 생성 실패: index=$index" }
            false
        }
    }

    /**
     * 인덱스를 삭제합니다.
     *
     * @param index 인덱스 이름
     */
    suspend fun deleteIndex(index: String): Boolean = withContext(Dispatchers.IO) {
        log.warn { "인덱스 삭제: index=$index" }

        try {
            elasticsearchClient.indices().delete { req ->
                req.index(index)
            }

            log.info { "인덱스 삭제 완료: index=$index" }
            true
        } catch (e: Exception) {
            log.error(e) { "인덱스 삭제 실패: index=$index" }
            false
        }
    }

    /**
     * 대량 인덱싱을 수행합니다.
     *
     * @param index 인덱스 이름
     * @param documents 문서 리스트 (ID와 문서 쌍)
     * @return 성공 개수
     */
    suspend fun <T> bulkIndex(
        index: String,
        documents: List<Pair<String, T>>
    ): Int = withContext(Dispatchers.IO) {
        log.info { "대량 인덱싱 시작: index=$index, count=${documents.size}" }

        val bulkRequest = BulkRequest.Builder()

        documents.forEach { (id, doc) ->
            bulkRequest.operations { op ->
                op.index { idx ->
                    idx.index(index)
                        .id(id)
                        .document(doc)
                }
            }
        }

        val response = elasticsearchClient.bulk(bulkRequest.build())

        val successCount = response.items().count { !it.error().isPresent }
        val errorCount = response.items().count { it.error().isPresent }

        log.info { "대량 인덱싱 완료: success=$successCount, error=$errorCount" }

        successCount
    }
}

/**
 * 검색 결과
 */
data class SearchResult<T>(
    val hits: List<SearchHit<T>>,
    val total: Long,
    val took: Long
)

/**
 * 검색 히트
 */
data class SearchHit<T>(
    val id: String,
    val score: Double,
    val source: T
)

/**
 * Elasticsearch 문서 인터페이스
 */
interface ElasticDocument {
    val id: String
    val createdAt: ZonedDateTime
    val updatedAt: ZonedDateTime
}

/**
 * Elasticsearch 예외
 */
class ElasticSearchException(message: String, cause: Throwable? = null) :
    RuntimeException(message, cause)
