USE [MunicipalSentiment]
GO

-- 1. Redes Sociais
-- Insira manualmente: 'Bluesky', 'Reddit', 'Facebook', 'GoogleNews', 'YouTube'
CREATE TABLE [dbo].[SocialNetwork](
    [SNetwork_ID]   INT          IDENTITY(1,1) NOT NULL,
    [SNetwork_Name] VARCHAR(50)  NOT NULL,
    [EntryDate_SN]  DATETIME     DEFAULT GETDATE(),
 
    CONSTRAINT [PK_SocialNetwork]
        PRIMARY KEY ([SNetwork_ID]),
 
    CONSTRAINT [UQ_SocialNetwork_Name]
        UNIQUE ([SNetwork_Name])
);

-- 2. Utilizadores / Canais (UserSN)
CREATE TABLE [dbo].[UserSN](
    [User_ID]      BIGINT        IDENTITY(1,1) NOT NULL,
    [Handle]       NVARCHAR(255) NULL,
    [SNetwork_ID]  INT           NULL,
    [EntryDate_U]  DATETIME      DEFAULT GETDATE(),
 
    CONSTRAINT [PK_UserSN]
        PRIMARY KEY ([User_ID]),
 
    CONSTRAINT [FK_UserSN_SocialNetwork]
        FOREIGN KEY ([SNetwork_ID])
        REFERENCES [dbo].[SocialNetwork] ([SNetwork_ID])
);

-- 3. Tabela Principal de Conteúdo (Posts, Vídeos, Notícias)
CREATE TABLE [dbo].[Post](
    [Post_ID]              BIGINT        IDENTITY(1,1) NOT NULL,
    [Original_External_ID] NVARCHAR(500) NULL,  -- platform_id: URL, URI, post_id
    [User_ID]              BIGINT        NULL,
    [SNetwork_ID]          INT           NOT NULL,
    [CreatedAt]            DATETIME      NULL,
    [Title]                NVARCHAR(MAX) NULL,
    [Content]              NVARCHAR(MAX) NULL,
    [URL]                  NVARCHAR(MAX) NULL,
    [ViewCount]            BIGINT        DEFAULT 0,
    [LikeCount]            BIGINT        DEFAULT 0,
    [ReplyCount]           BIGINT        DEFAULT 0,
    [EntryDate_DB]         DATETIME      DEFAULT GETDATE(),
 
    CONSTRAINT [PK_Post]
        PRIMARY KEY CLUSTERED ([Post_ID] ASC),
 
    CONSTRAINT [FK_Post_UserSN]
        FOREIGN KEY ([User_ID])
        REFERENCES [dbo].[UserSN] ([User_ID]),
 
    CONSTRAINT [FK_Post_SocialNetwork]
        FOREIGN KEY ([SNetwork_ID])
        REFERENCES [dbo].[SocialNetwork] ([SNetwork_ID])
);

-- 4. Tabela de Comentários e Respostas
CREATE TABLE [dbo].[Comment](
    [Comment_ID]         BIGINT        IDENTITY(1,1) NOT NULL,
    [Post_ID]            BIGINT        NOT NULL,
    [External_Comment_ID] NVARCHAR(500) NULL,
    [Parent_Comment_ID]  BIGINT        NULL,
    [Author_Handle]      NVARCHAR(255) NULL,
    [Comment_Text]       NVARCHAR(MAX) NULL,
    [Likes_Upvotes]      INT           DEFAULT 0,
    [CreatedAt]          DATETIME      NULL,
    [EntryDate_DB]       DATETIME      DEFAULT GETDATE(),
 
    CONSTRAINT [PK_Comment]
        PRIMARY KEY ([Comment_ID]),
 
    CONSTRAINT [FK_Comment_Post]
        FOREIGN KEY ([Post_ID])
        REFERENCES [dbo].[Post] ([Post_ID]),
 
    CONSTRAINT [FK_Comment_Parent]
        FOREIGN KEY ([Parent_Comment_ID])
        REFERENCES [dbo].[Comment] ([Comment_ID])
);

-- 5. Tabela intermédia para textos a analisar

CREATE TABLE [dbo].[TextDocument](
    [TextDocument_ID] BIGINT        IDENTITY(1,1) NOT NULL,
    [Source_Type]     VARCHAR(20)   NOT NULL,  -- 'POST' ou 'COMMENT'
    [Post_ID]         BIGINT        NULL,
    [Comment_ID]      BIGINT        NULL,
    [SNetwork_ID]     INT           NOT NULL,
    [Original_Text]   NVARCHAR(MAX) NULL,
    [Clean_Text]      NVARCHAR(MAX) NULL,
    [Language]        VARCHAR(10)   NULL,       -- 'pt', 'en', 'es'
    [Municipality]    NVARCHAR(100) NULL,
    [CreatedAt]       DATETIME      NULL,
    [ProcessedAt]     DATETIME      DEFAULT GETDATE(),
 
    CONSTRAINT [PK_TextDocument]
        PRIMARY KEY ([TextDocument_ID]),
 
    CONSTRAINT [FK_TextDocument_Post]
        FOREIGN KEY ([Post_ID])
        REFERENCES [dbo].[Post] ([Post_ID]),
 
    CONSTRAINT [FK_TextDocument_Comment]
        FOREIGN KEY ([Comment_ID])
        REFERENCES [dbo].[Comment] ([Comment_ID]),
 
    CONSTRAINT [FK_TextDocument_SocialNetwork]
        FOREIGN KEY ([SNetwork_ID])
        REFERENCES [dbo].[SocialNetwork] ([SNetwork_ID]),
 
    CONSTRAINT [CK_TextDocument_SourceType]
        CHECK ([Source_Type] IN ('POST', 'COMMENT')),
 
    CONSTRAINT [CK_TextDocument_OnlyOneSource]
        CHECK (
            ([Source_Type] = 'POST'    AND [Post_ID]    IS NOT NULL AND [Comment_ID] IS NULL)
            OR
            ([Source_Type] = 'COMMENT' AND [Comment_ID] IS NOT NULL)
        )
);


-- 6. Tabela de Análise de Sentimentos
CREATE TABLE [dbo].[SentimentAnalysis](
    [Sentiment_ID]      BIGINT        IDENTITY(1,1) NOT NULL,
    [TextDocument_ID]   BIGINT        NOT NULL,
    [Sentiment_Label]   VARCHAR(20)   NOT NULL,  -- POSITIVE, NEGATIVE, NEUTRAL
    [Sentiment_Score]   FLOAT         NULL,       -- positive - negative (continuo)
    [Negative]          FLOAT         NULL,
    [Neutral]           FLOAT         NULL,
    [Positive]          FLOAT         NULL,
    [Comments_Polarity] FLOAT         NULL,       -- media de polaridade dos comentarios (Reddit)
    [Model_Name]        NVARCHAR(255) NULL,
    [Model_Version]     NVARCHAR(100) NULL,
    [AnalyzedAt]        DATETIME      DEFAULT GETDATE(),
 
    CONSTRAINT [PK_SentimentAnalysis]
        PRIMARY KEY ([Sentiment_ID]),
 
    CONSTRAINT [FK_SentimentAnalysis_TextDocument]
        FOREIGN KEY ([TextDocument_ID])
        REFERENCES [dbo].[TextDocument] ([TextDocument_ID]),
 
    CONSTRAINT [CK_Sentiment_Label]
        CHECK ([Sentiment_Label] IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL'))
);


-- 7. Tabela de Análise de Emoções
CREATE TABLE [dbo].[EmotionAnalysis](
    [Emotion_ID]        BIGINT        IDENTITY(1,1) NOT NULL,
    [TextDocument_ID]   BIGINT        NOT NULL,
    [Dominant_Emotion]  VARCHAR(50)   NOT NULL,
    [Confidence]        FLOAT         NULL,
    [Active_Emotions]   NVARCHAR(500) NULL,  -- emocoes acima do threshold, separadas por virgula
    [Emotion_Scores]    NVARCHAR(MAX) NULL,  -- JSON com todos os 11 scores
    [Model_Name]        NVARCHAR(255) NULL,
    [Model_Version]     NVARCHAR(100) NULL,
    [AnalyzedAt]        DATETIME      DEFAULT GETDATE(),
 
    CONSTRAINT [PK_EmotionAnalysis]
        PRIMARY KEY ([Emotion_ID]),
 
    CONSTRAINT [FK_EmotionAnalysis_TextDocument]
        FOREIGN KEY ([TextDocument_ID])
        REFERENCES [dbo].[TextDocument] ([TextDocument_ID]),
 
    CONSTRAINT [CK_Dominant_Emotion]
        CHECK ([Dominant_Emotion] IN (
            'ANGER', 'CONTEMPT', 'DISGUST', 'FEAR',
            'FRUSTRATION', 'GRATITUDE', 'JOY',
            'LOVE', 'NEUTRAL', 'SADNESS', 'SURPRISE'
        ))
);

-- 8. KEYWORDS
CREATE TABLE [dbo].[Keyword](
    [Keyword_ID]      BIGINT         IDENTITY(1,1) NOT NULL,
    [TextDocument_ID] BIGINT         NOT NULL,
    [Keyword_Text]    NVARCHAR(500)  NOT NULL,
    [Score]           FLOAT          NULL,
    [ExtractedAt]     DATETIME       DEFAULT GETDATE(),
 
    CONSTRAINT [PK_Keyword]
        PRIMARY KEY ([Keyword_ID]),
 
    CONSTRAINT [FK_Keyword_TextDocument]
        FOREIGN KEY ([TextDocument_ID])
        REFERENCES [dbo].[TextDocument] ([TextDocument_ID])
);


-- 9. ENTIDADES NER
CREATE TABLE [dbo].[NamedEntity](
    [Entity_ID]       BIGINT         IDENTITY(1,1) NOT NULL,
    [TextDocument_ID] BIGINT         NOT NULL,
    [Entity_Text]     NVARCHAR(500)  NOT NULL,
    [Entity_Label]    VARCHAR(10)    NOT NULL,  -- PER, ORG, LOC, MISC
    [ExtractedAt]     DATETIME       DEFAULT GETDATE(),
 
    CONSTRAINT [PK_NamedEntity]
        PRIMARY KEY ([Entity_ID]),
 
    CONSTRAINT [FK_NamedEntity_TextDocument]
        FOREIGN KEY ([TextDocument_ID])
        REFERENCES [dbo].[TextDocument] ([TextDocument_ID]),
 
    CONSTRAINT [CK_Entity_Label]
        CHECK ([Entity_Label] IN ('PER', 'ORG', 'LOC', 'MISC'))
);


-- 10. TOPICOS BERTOPIC
CREATE TABLE [dbo].[TopicAssignment](
    [TopicAssignment_ID] BIGINT         IDENTITY(1,1) NOT NULL,
    [TextDocument_ID]    BIGINT         NOT NULL,
    [Topic_ID]           INT            NOT NULL,  -- -1 = outlier (sem topico)
    [Topic_Probability]  FLOAT          NULL,
    [Topic_Keywords]     NVARCHAR(MAX)  NULL,  -- keywords do topico separadas por virgula
    [Model_Version]      NVARCHAR(100)  NULL,  -- data do treino do modelo
    [AssignedAt]         DATETIME       DEFAULT GETDATE(),
 
    CONSTRAINT [PK_TopicAssignment]
        PRIMARY KEY ([TopicAssignment_ID]),
 
    CONSTRAINT [FK_TopicAssignment_TextDocument]
        FOREIGN KEY ([TextDocument_ID])
        REFERENCES [dbo].[TextDocument] ([TextDocument_ID])
);


-- Índices para performance

-- Post
CREATE INDEX [IX_Post_ExternalID]
    ON [dbo].[Post] ([Original_External_ID]);
 
CREATE INDEX [IX_Post_SNetwork]
    ON [dbo].[Post] ([SNetwork_ID]);
 
CREATE INDEX [IX_Post_CreatedAt]
    ON [dbo].[Post] ([CreatedAt]);
 
-- Comment
CREATE INDEX [IX_Comment_ExternalID]
    ON [dbo].[Comment] ([External_Comment_ID]);
 
CREATE INDEX [IX_Comment_Post]
    ON [dbo].[Comment] ([Post_ID]);
 
-- TextDocument
CREATE INDEX [IX_TextDocument_Post]
    ON [dbo].[TextDocument] ([Post_ID]);
 
CREATE INDEX [IX_TextDocument_SNetwork]
    ON [dbo].[TextDocument] ([SNetwork_ID]);
 
-- SentimentAnalysis
CREATE INDEX [IX_Sentiment_TextDocument]
    ON [dbo].[SentimentAnalysis] ([TextDocument_ID]);
 
CREATE INDEX [IX_Sentiment_Label]
    ON [dbo].[SentimentAnalysis] ([Sentiment_Label]);
 
-- EmotionAnalysis
CREATE INDEX [IX_Emotion_TextDocument]
    ON [dbo].[EmotionAnalysis] ([TextDocument_ID]);
 
CREATE INDEX [IX_Emotion_Dominant]
    ON [dbo].[EmotionAnalysis] ([Dominant_Emotion]);
 
-- Keyword
CREATE INDEX [IX_Keyword_TextDocument]
    ON [dbo].[Keyword] ([TextDocument_ID]);
 
-- NamedEntity
CREATE INDEX [IX_NamedEntity_TextDocument]
    ON [dbo].[NamedEntity] ([TextDocument_ID]);
 
CREATE INDEX [IX_NamedEntity_Label]
    ON [dbo].[NamedEntity] ([Entity_Label]);
 
-- TopicAssignment
CREATE INDEX [IX_Topic_TextDocument]
    ON [dbo].[TopicAssignment] ([TextDocument_ID]);
 
CREATE INDEX [IX_Topic_ID]
    ON [dbo].[TopicAssignment] ([Topic_ID]);
 
GO


