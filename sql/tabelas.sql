USE [SNCrawler]
GO

-- 1. Redes Sociais
-- Insira manualmente: 'Bluesky', 'Reddit', 'Facebook', 'GoogleNews', 'YouTube'
CREATE TABLE [dbo].[SocialNetwork](
    [SNetwork_ID] INT IDENTITY(1,1) NOT NULL,
    [SNetwork_Name] VARCHAR(50) NOT NULL,
    [EntryDate_SN] DATETIME DEFAULT GETDATE(),

    CONSTRAINT [PK_SocialNetwork] 
        PRIMARY KEY ([SNetwork_ID]),

    CONSTRAINT [UQ_SocialNetwork_Name]
        UNIQUE ([SNetwork_Name])
);

-- 2. Utilizadores / Canais (UserSN)
CREATE TABLE [dbo].[UserSN](
    [User_ID] BIGINT IDENTITY(1,1) NOT NULL,
    [Handle] NVARCHAR(255) NULL,
    [SNetwork_ID] INT NULL,
    [EntryDate_U] DATETIME DEFAULT GETDATE(),

    CONSTRAINT [PK_UserSN]
        PRIMARY KEY ([User_ID]),

    CONSTRAINT [FK_UserSN_SocialNetwork]
        FOREIGN KEY ([SNetwork_ID]) 
        REFERENCES [dbo].[SocialNetwork] ([SNetwork_ID])
);

-- 3. Tabela Principal de Conteúdo (Posts, Vídeos, Notícias)
CREATE TABLE [dbo].[Post](
	[Post_ID] BIGINT IDENTITY(1,1) NOT NULL,
	[Original_External_ID] NVARCHAR(500) NULL, -- video_id, post_id, URI ou URL
	[User_ID] BIGINT NULL,                    -- FK para o autor/canal
	[SNetwork_ID] INT NOT NULL,
	[CreatedAt] DATETIME NULL,                -- published_date ou created_time
	[Title] NVARCHAR(MAX) NULL,               -- Título do vídeo ou da notícia
	[Content] NVARCHAR(MAX) NULL,             -- Descrição do vídeo ou texto do post
	[URL] NVARCHAR(MAX) NULL,                 -- video_url ou link da notícia
	[ViewCount] BIGINT DEFAULT 0,             -- EXCLUSIVO YOUTUBE: número de visualizações
	[LikeCount] BIGINT DEFAULT 0,             -- likes ou upvotes
	[ReplyCount] BIGINT DEFAULT 0,            -- comments_count ou total de respostas
	[EntryDate_DB] DATETIME DEFAULT GETDATE(),
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
	[Comment_ID] BIGINT IDENTITY(1,1) NOT NULL,
	[Post_ID] BIGINT NOT NULL,                -- ID do Post/Vídeo de origem
	[External_Comment_ID] NVARCHAR(500) NULL, -- comment_id do YouTube/FB
	[Parent_Comment_ID] BIGINT NULL,          -- PARA YOUTUBE: Se for uma resposta, aponta para o ID do comentário pai
	[Author_Handle] NVARCHAR(255) NULL,       -- Nome de quem comentou
	[Comment_Text] NVARCHAR(MAX) NULL,
	[Likes_Upvotes] INT DEFAULT 0,
	[CreatedAt] DATETIME NULL,
    [EntryDate_DB] DATETIME DEFAULT GETDATE(),
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
    [TextDocument_ID] BIGINT IDENTITY(1,1) NOT NULL,
    [Source_Type] VARCHAR(20) NOT NULL, -- 'POST' ou 'COMMENT'
    [Post_ID] BIGINT NULL,
    [Comment_ID] BIGINT NULL,
    [SNetwork_ID] INT NOT NULL,
    [Original_Text] NVARCHAR(MAX) NULL, -- texto original antes da limpeza
    [Clean_Text] NVARCHAR(MAX) NULL, -- texto limpo e normalizado
    [Language] VARCHAR(10) NULL, -- exemplo: 'pt', 'en', 'es'
    [Municipality] NVARCHAR(100) NULL, -- município associado, se conseguires identificar
    [CreatedAt] DATETIME NULL, -- data original do post/comentário
    [ProcessedAt] DATETIME DEFAULT GETDATE(),
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
            ([Source_Type] = 'POST' AND [Post_ID] IS NOT NULL AND [Comment_ID] IS NULL)
            OR
            ([Source_Type] = 'COMMENT' AND [Comment_ID] IS NOT NULL)
        )
);


-- 6. Tabela de Análise de Sentimentos

CREATE TABLE [dbo].[SentimentAnalysis](
    [Sentiment_ID] BIGINT IDENTITY(1,1) NOT NULL,
    [TextDocument_ID] BIGINT NOT NULL,
    [Sentiment_Label] VARCHAR(20) NOT NULL, -- POSITIVE, NEGATIVE, NEUTRAL
    [Confidence] FLOAT NULL,
    [Model_Name] NVARCHAR(255) NULL,
    [Model_Version] NVARCHAR(100) NULL,
    [AnalyzedAt] DATETIME DEFAULT GETDATE(),
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
    [Emotion_ID] BIGINT IDENTITY(1,1) NOT NULL,
    [TextDocument_ID] BIGINT NOT NULL,
    [Emotion_Label] VARCHAR(50) NOT NULL, -- ANGER, JOY, SADNESS, FEAR, SURPRISE, DISGUST, NEUTRAL
    [Confidence] FLOAT NULL,
    [Model_Name] NVARCHAR(255) NULL,
    [Model_Version] NVARCHAR(100) NULL,
    [AnalyzedAt] DATETIME DEFAULT GETDATE(),
    CONSTRAINT [PK_EmotionAnalysis]
        PRIMARY KEY ([Emotion_ID]),

    CONSTRAINT [FK_EmotionAnalysis_TextDocument]
        FOREIGN KEY ([TextDocument_ID])
        REFERENCES [dbo].[TextDocument] ([TextDocument_ID]),

    CONSTRAINT [CK_Emotion_Label]
        CHECK ([Emotion_Label] IN (
            'ANGER',
            'JOY',
            'SADNESS',
            'FEAR',
            'SURPRISE',
            'DISGUST',
            'NEUTRAL'
        ))
);

-- Índices para performance
CREATE INDEX IX_OriginalID ON [dbo].[Post] (Original_External_ID);
CREATE INDEX IX_ExternalCommentID ON [dbo].[Comment] (External_Comment_ID);
GO