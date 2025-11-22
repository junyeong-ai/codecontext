# Cache Policy

| 도메인       | 패턴                      | 유지시간  | 만료정책                | 비고                        | 
|-----------|---------------------------|-------|-------------------------|---------------------------|
| dashboard | dashboard:org-id:api-name | 10min | order/alert/settlement  | 변경 요소가 많을 경우 시간 기반  |

## 이벤트 밸생시 캐시 만료 정책
각 도메인 에서 CUD시
eventPublisher.notifyDomainChanged(domain, org-id, user-id)
CacheLoader가 수신 하여 관련 캐시 제거

Settlement CUD
* dashboard:org-id:*

Order CUD
* dashboard:org-id:*

User ALRERT CUD
* dashboard:user-id:*
* 




# Spring Cache 가이드

@Cacheable("cacheName") : 캐시에 데이터를 저장하고, 캐시에 데이터가 존재하면 캐시에서 데이터를 가져온다.
네임은 설정에 있습니다.
key는 해당 함수의 아규먼트에 의해 만들어 지지만,
적절치 않을수도 있어 key 생성기를 설정 하기도 합니다. 

```kotlin
@Cacheable(
    cacheManager = cacheManager,
    cacheNames = "uniqueCacheName", 
    key = "#serviceType.name()",
    unless = "#result == null"
)
suspend fun getXXXXX(serviceType: ServiceType): XXXXX {
    return XXXXX
}
```

키생성 방식은 
없는 인자 이름을 넣어도 오류가 나지 않으니 주의해야 합니다. (null로 되겠죠, null키로 캐싱됩니다)
```kotlin
@Cacheable(cacheNames = ["calc"], key = "#x + '::' + #name" ) // JoinPoint 인자 x,y 로 key를 생성
fun calc(x: Int, name: String): Nothing

```

## Reference
추후 다양한 설정을 하려면...
https://www.baeldung.com/spring-multiple-cache-managers


## redis
topic:admin

channel
"sse:topics:00000000-0000-0000-0000-000000000000"

## KEYS
캐시 컨텐츠
거래처 (partner)
    빈도 낮음, 시간으로만 캐싱

location, vehicle 캐싱과 만료 이벤트 -> upsert로 인해 불일치 가능성 높음
