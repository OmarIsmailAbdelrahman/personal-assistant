## Android UI Integration Guide

### Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                 ANDROID APP LAYERS                       │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │              UI LAYER (Jetpack Compose)            │ │
│  │                                                    │ │
│  │  • LoginScreen                                     │ │
│  │  • RegistrationScreen                              │ │
│  │  • ConversationListScreen                          │ │
│  │  • ChatScreen (main interface)                     │ │
│  │  • MessageList (RecyclerView/LazyColumn)           │ │
│  │  • ImageViewer                                     │ │
│  └───────────────────┬────────────────────────────────┘ │
│                      │                                   │
│  ┌───────────────────▼────────────────────────────────┐ │
│  │          VIEW MODEL LAYER (MVVM)                   │ │
│  │                                                    │ │
│  │  • AuthViewModel                                   │ │
│  │  • ChatViewModel                                   │ │
│  │  • ConversationViewModel                           │ │
│  │                                                    │ │
│  │  Responsibilities:                                 │ │
│  │  - Hold UI state                                   │ │
│  │  - Handle user actions                             │ │
│  │  - Call repository methods                         │ │
│  │  - Manage polling coroutines                       │ │
│  └───────────────────┬────────────────────────────────┘ │
│                      │                                   │
│  ┌───────────────────▼────────────────────────────────┐ │
│  │          REPOSITORY LAYER                          │ │
│  │                                                    │ │
│  │  • AuthRepository                                  │ │
│  │  • ConversationRepository                          │ │
│  │  • MessageRepository                               │ │
│  │                                                    │ │
│  │  Responsibilities:                                 │ │
│  │  - Abstract data sources                           │ │
│  │  - Cache management                                │ │
│  │  - Coordinate remote + local data                  │ │
│  └───────────────────┬────────────────────────────────┘ │
│                      │                                   │
│  ┌───────────────────▼────────────────────────────────┐ │
│  │          DATA LAYER                                │ │
│  │                                                    │ │
│  │  Remote:              Local:                       │ │
│  │  • Retrofit API       • Room Database              │ │
│  │  • OkHttp interceptor • SharedPreferences          │ │
│  │                       • EncryptedSharedPrefs       │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │  BACKEND API        │
            │  http://VM_IP:60100 │
            └─────────────────────┘
```

---

### Project Setup

#### 1. Create New Android Project

```kotlin
// build.gradle.kts (Project level)
plugins {
    id("com.android.application") version "8.2.0" apply false
    id("org.jetbrains.kotlin.android") version "1.9.20" apply false
    id("com.google.devtools.ksp") version "1.9.20-1.0.14" apply false
}
```

```kotlin
// build.gradle.kts (App level)
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
    kotlin("plugin.serialization") version "1.9.20"
}

dependencies {
    // Jetpack Compose
    implementation("androidx.compose.ui:ui:1.5.4")
    implementation("androidx.compose.material3:material3:1.1.2")
    implementation("androidx.compose.ui:ui-tooling-preview:1.5.4")
    implementation("androidx.activity:activity-compose:1.8.1")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.6.2")
    implementation("androidx.navigation:navigation-compose:2.7.5")
    
    // Networking
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    
    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    
    // Room (local database)
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")
    
    // Encrypted SharedPreferences
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    
    // Image loading (Coil)
    implementation("io.coil-kt:coil-compose:2.5.0")
    
    // Serialization
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.0")
}
```

---

### 2. API Client Setup

#### Network Module

```kotlin
// data/remote/ApiConfig.kt
object ApiConfig {
    const val BASE_URL = "http://192.168.1.100:60100/" // Replace with your VM IP
    const val TIMEOUT_SECONDS = 30L
}

// data/remote/AuthInterceptor.kt
class AuthInterceptor(private val tokenManager: TokenManager) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val token = tokenManager.getToken()
        
        val newRequest = if (token != null) {
            request.newBuilder()
                .addHeader("Authorization", "Bearer $token")
                .build()
        } else {
            request
        }
        
        return chain.proceed(newRequest)
    }
}

// data/remote/RetrofitClient.kt
object RetrofitClient {
    private lateinit var tokenManager: TokenManager
    
    fun initialize(context: Context) {
        tokenManager = TokenManager(context)
    }
    
    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(AuthInterceptor(tokenManager))
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        })
        .connectTimeout(ApiConfig.TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .readTimeout(ApiConfig.TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .writeTimeout(ApiConfig.TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .build()
    
    val api: ChatApi by lazy {
        Retrofit.Builder()
            .baseUrl(ApiConfig.BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ChatApi::class.java)
    }
}
```

#### API Interface

```kotlin
// data/remote/ChatApi.kt
interface ChatApi {
    // Authentication
    @POST("v1/auth/register")
    suspend fun register(@Body request: RegisterRequest): AuthResponse
    
    @POST("v1/auth/login")
    suspend fun login(@Body request: LoginRequest): AuthResponse
    
    // Conversations
    @POST("v1/conversations")
    suspend fun createConversation(@Body request: CreateConversationRequest): ConversationResponse
    
    @GET("v1/conversations/{id}")
    suspend fun getConversation(@Path("id") id: String): ConversationResponse
    
    // Messages
    @POST("v1/conversations/{id}/messages")
    suspend fun postMessage(
        @Path("id") conversationId: String,
        @Body request: MessageRequest
    ): MessagePostResponse
    
    @GET("v1/conversations/{id}/messages")
    suspend fun getMessages(
        @Path("id") conversationId: String,
        @Query("since") since: String? = null
    ): List<MessageResponse>
    
    // Agent Runs
    @GET("v1/runs/{id}")
    suspend fun getRunStatus(@Path("id") runId: String): RunResponse
    
    // Media
    @GET("v1/media/{id}")
    suspend fun downloadMedia(@Path("id") mediaId: String): ResponseBody
    
    // Health
    @GET("health")
    suspend fun health(): HealthResponse
}
```

#### Data Models

```kotlin
// data/models/AuthModels.kt
data class RegisterRequest(
    val email: String,
    val password: String
)

data class LoginRequest(
    val email: String,
    val password: String
)

data class AuthResponse(
    val access_token: String,
    val token_type: String,
    val user_id: String
)

// data/models/MessageModels.kt
data class MessageRequest(
    val text: String
)

data class MessagePostResponse(
    val message_id: String,
    val run_id: String,
    val status: String
)

data class MessageResponse(
    val id: String,
    val sender: String,  // "user", "assistant", "system"
    val content_json: MessageContent,
    val created_at: String
)

data class MessageContent(
    val type: String,  // "text" or "image"
    val text: String? = null,
    val url: String? = null,
    val caption: String? = null
)

// data/models/ConversationModels.kt
data class CreateConversationRequest(
    val title: String
)

data class ConversationResponse(
    val id: String,
    val title: String?,
    val created_at: String
)

// data/models/RunModels.kt
data class RunResponse(
    val id: String,
    val status: String,  // "queued", "running", "succeeded", "failed"
    val started_at: String?,
    val finished_at: String?,
    val last_error: String?
)
```

---

### 3. Token Management (Secure Storage)

```kotlin
// data/local/TokenManager.kt
class TokenManager(context: Context) {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()
    
    private val sharedPreferences = EncryptedSharedPreferences.create(
        context,
        "auth_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    
    fun saveToken(token: String) {
        sharedPreferences.edit().putString(KEY_TOKEN, token).apply()
    }
    
    fun getToken(): String? {
        return sharedPreferences.getString(KEY_TOKEN, null)
    }
    
    fun clearToken() {
        sharedPreferences.edit().remove(KEY_TOKEN).apply()
    }
    
    fun isLoggedIn(): Boolean {
        return getToken() != null
    }
    
    companion object {
        private const val KEY_TOKEN = "jwt_token"
    }
}
```

---

### 4. Repository Layer

```kotlin
// data/repository/AuthRepository.kt
class AuthRepository(
    private val api: ChatApi,
    private val tokenManager: TokenManager
) {
    suspend fun register(email: String, password: String): Result<AuthResponse> {
        return try {
            val response = api.register(RegisterRequest(email, password))
            tokenManager.saveToken(response.access_token)
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun login(email: String, password: String): Result<AuthResponse> {
        return try {
            val response = api.login(LoginRequest(email, password))
            tokenManager.saveToken(response.access_token)
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    fun logout() {
        tokenManager.clearToken()
    }
}

// data/repository/MessageRepository.kt
class MessageRepository(
    private val api: ChatApi,
    private val messageDao: MessageDao // Room DAO for local cache
) {
    suspend fun postMessage(
        conversationId: String,
        text: String
    ): Result<MessagePostResponse> {
        return try {
            val response = api.postMessage(
                conversationId,
                MessageRequest(text)
            )
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun getMessages(
        conversationId: String,
        since: String? = null
    ): Result<List<MessageResponse>> {
        return try {
            val messages = api.getMessages(conversationId, since)
            
            // Cache locally
            messageDao.insertAll(messages.map { it.toEntity(conversationId) })
            
            Result.success(messages)
        } catch (e: Exception) {
            // Return cached messages if offline
            val cached = messageDao.getMessagesForConversation(conversationId)
            if (cached.isNotEmpty()) {
                Result.success(cached.map { it.toResponse() })
            } else {
                Result.failure(e)
            }
        }
    }
}
```

---

### 5. ViewModel with Polling

```kotlin
// ui/chat/ChatViewModel.kt
class ChatViewModel(
    private val messageRepository: MessageRepository,
    private val runRepository: RunRepository,
    private val conversationId: String
) : ViewModel() {
    private val _messages = MutableStateFlow<List<MessageResponse>>(emptyList())
    val messages: StateFlow<List<MessageResponse>> = _messages.asStateFlow()
    
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()
    
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()
    
    private val pollingJob: Job
    
    init {
        // Start polling for messages every 3 seconds
        pollingJob = viewModelScope.launch {
            while (isActive) {
                fetchMessages()
                delay(3000) // Poll every 3 seconds
            }
        }
    }
    
    fun sendMessage(text: String) {
        viewModelScope.launch {
            _isLoading.value = true
            
            messageRepository.postMessage(conversationId, text).fold(
                onSuccess = { response ->
                    // Message sent, worker will process it
                    // Immediately add optimistic UI update
                    val optimisticMessage = MessageResponse(
                        id = "temp-${System.currentTimeMillis()}",
                        sender = "user",
                        content_json = MessageContent(type = "text", text = text),
                        created_at = System.currentTimeMillis().toString()
                    )
                    _messages.value = _messages.value + optimisticMessage
                    
                    // Fetch messages sooner to get assistant response
                    delay(500)
                    fetchMessages()
                },
                onFailure = { error ->
                    _error.value = error.message
                }
            )
            
            _isLoading.value = false
        }
    }
    
    private suspend fun fetchMessages() {
        messageRepository.getMessages(conversationId).fold(
            onSuccess = { fetchedMessages ->
                _messages.value = fetchedMessages
            },
            onFailure = {
                // Silently fail, keep showing cached
            }
        )
    }
    
    override fun onCleared() {
        super.onCleared()
        pollingJob.cancel()
    }
}
```

---

### 6. Compose UI

```kotlin
// ui/chat/ChatScreen.kt
@Composable
fun ChatScreen(
    conversationId: String,
    viewModel: ChatViewModel = rememberViewModel { ChatViewModel(..., conversationId) }
) {
    val messages by viewModel.messages.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    
    var inputText by remember { mutableStateOf("") }
    
    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Chat") })
        },
        bottomBar = {
            MessageInputBar(
                text = inputText,
                onTextChange = { inputText = it },
                onSend = {
                    if (inputText.isNotBlank()) {
                        viewModel.sendMessage(inputText)
                        inputText = ""
                    }
                },
                enabled = !isLoading
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            reverseLayout = true  // New messages at bottom
        ) {
            items(messages.reversed()) { message ->
                MessageBubble(message)
            }
        }
    }
}

@Composable
fun MessageBubble(message: MessageResponse) {
    val isUser = message.sender == "user"
    
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(8.dp),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
    ) {
        Card(
            colors = CardDefaults.cardColors(
                containerColor = if (isUser) MaterialTheme.colorScheme.primary
                else MaterialTheme.colorScheme.surfaceVariant
            ),
            modifier = Modifier.widthIn(max = 280.dp)
        ) {
            when (message.content_json.type) {
                "text" -> {
                    Text(
                        text = message.content_json.text ?: "",
                        modifier = Modifier.padding(12.dp),
                        color = if (isUser) MaterialTheme.colorScheme.onPrimary
                        else MaterialTheme.colorScheme.onSurface
                    )
                }
                "image" -> {
                    AsyncImage(
                        model = ApiConfig.BASE_URL + message.content_json.url,
                        contentDescription = message.content_json.caption,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(200.dp)
                    )
                    if (message.content_json.caption != null) {
                        Text(
                            text = message.content_json.caption,
                            modifier = Modifier.padding(8.dp)
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun MessageInputBar(
    text: String,
    onTextChange: (String) -> Unit,
    onSend: () -> Unit,
    enabled: Boolean
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        OutlinedTextField(
            value = text,
            onValueChange = onTextChange,
            modifier = Modifier.weight(1f),
            placeholder = { Text("Type a message...") },
            enabled = enabled
        )
        
        Spacer(modifier = Modifier.width(8.dp))
        
        IconButton(
            onClick = onSend,
            enabled = enabled && text.isNotBlank()
        ) {
            Icon(Icons.Default.Send, contentDescription = "Send")
        }
    }
}
```

---

### 7. Complete Integration Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User types "Hello AI" and taps Send button                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ ChatScreen onClick                                          │
│ → viewModel.sendMessage("Hello AI")                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ ChatViewModel.sendMessage()                                 │
│ → messageRepository.postMessage(conversationId, "Hello AI")│
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ MessageRepository.postMessage()                             │
│ → api.postMessage() [Retrofit call]                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ HTTP POST to http://VM_IP:60100/v1/conversations/{id}/msgs│
│ Headers: Authorization: Bearer {JWT}                        │
│ Body: {"text": "Hello AI"}                                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend API receives request                                │
│ → Returns 202 Accepted with run_id                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Android receives response                                   │
│ → Add optimistic message to UI (immediate feedback)         │
│ → Start fetching messages more frequently                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Polling coroutine (every 3 seconds)                         │
│ → GET /v1/conversations/{id}/messages                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend returns messages array including AI response        │
│ [                                                           │
│   {sender: "user", text: "Hello AI"},                      │
│   {sender: "assistant", text: "Hello! How can I help?"}   │
│ ]                                                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Android receives new messages                               │
│ → Update StateFlow → Compose recomposes                    │
│ → User sees AI response appear in chat                      │
└─────────────────────────────────────────────────────────────┘
```

---

