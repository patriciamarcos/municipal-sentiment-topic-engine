INSERT INTO [dbo].[SocialNetwork] ([SNetwork_Name]) VALUES
('Bluesky'),
('Reddit'),
('GoogleNews'),
('YouTube'),
('Facebook');

SELECT * FROM [dbo].[SocialNetwork];


DROP INDEX [IX_Post_ExternalID] ON [dbo].[Post];

ALTER TABLE [dbo].[Post]
ALTER COLUMN [Original_External_ID] NVARCHAR(MAX);

DELETE FROM [dbo].[TopicAssignment];
DELETE FROM [dbo].[NamedEntity];
DELETE FROM [dbo].[Keyword];
DELETE FROM [dbo].[EmotionAnalysis];
DELETE FROM [dbo].[SentimentAnalysis];
DELETE FROM [dbo].[TextDocument];
DELETE FROM [dbo].[Comment];
DELETE FROM [dbo].[Post];
DELETE FROM [dbo].[UserSN];


SELECT TOP 5
    p.[Original_External_ID],
    ta.[Topic_ID],
    ta.[Topic_Keywords],
    ta.[AssignedAt]
FROM [dbo].[TopicAssignment] ta
JOIN [dbo].[TextDocument] td ON ta.[TextDocument_ID] = td.[TextDocument_ID]
JOIN [dbo].[Post] p ON td.[Post_ID] = p.[Post_ID]
ORDER BY ta.[AssignedAt] DESC

SELECT TOP 10
    [Original_External_ID],
    [Source_Name]
FROM [dbo].[Post]
WHERE [Source_Name] IS NOT NULL
ORDER BY [Post_ID] ASC

ALTER TABLE [dbo].[Post]
ADD [Source_Name] NVARCHAR(255) NULL;


SELECT Sentiment_Label, COUNT(*) as Total
FROM [dbo].[SentimentAnalysis]
GROUP BY Sentiment_Label
ORDER BY Total DESC

SELECT Dominant_Emotion, COUNT(*) as Total
FROM [dbo].[EmotionAnalysis]
GROUP BY Dominant_Emotion
ORDER BY Total DESC

SELECT TOP 10 Entity_Text, Entity_Label, COUNT(*) as Total
FROM [dbo].[NamedEntity]
GROUP BY Entity_Text, Entity_Label
ORDER BY Total DESC

SELECT Topic_ID, COUNT(*) as Total
FROM [dbo].[TopicAssignment]
WHERE Topic_ID != -1
GROUP BY Topic_ID
ORDER BY Total DESC

SELECT Active_Emotions, COUNT(*) as Total
FROM [dbo].[EmotionAnalysis]
WHERE Dominant_Emotion = 'NEUTRAL'
GROUP BY Active_Emotions
ORDER BY Total DESC

SELECT 
    value as Emotion,
    COUNT(*) as Total
FROM [dbo].[EmotionAnalysis]
CROSS APPLY STRING_SPLIT(Active_Emotions, ',')
WHERE Dominant_Emotion = 'NEUTRAL'
  AND Active_Emotions != 'NEUTRAL'
  AND value != 'NEUTRAL'
  AND value != ' NEUTRAL'
GROUP BY value
ORDER BY Total DESC

-- Sentimento dos posts vs polaridade dos comentários Reddit
SELECT 
    sa.Sentiment_Label,
    COUNT(*) as Total_Posts,
    AVG(sa.Comments_Polarity) as Media_Polaridade_Comentarios,
    MIN(sa.Comments_Polarity) as Min_Polaridade,
    MAX(sa.Comments_Polarity) as Max_Polaridade
FROM [dbo].[SentimentAnalysis] sa
JOIN [dbo].[TextDocument] td ON sa.TextDocument_ID = td.TextDocument_ID
JOIN [dbo].[Post] p ON td.Post_ID = p.Post_ID
JOIN [dbo].[SocialNetwork] sn ON p.SNetwork_ID = sn.SNetwork_ID
WHERE sn.SNetwork_Name = 'Reddit'
  AND sa.Comments_Polarity IS NOT NULL
GROUP BY sa.Sentiment_Label
ORDER BY sa.Sentiment_Label

-- Sentimento por tópico
SELECT 
    ta.Topic_ID,
    sa.Sentiment_Label,
    COUNT(*) as Total
FROM [dbo].[SentimentAnalysis] sa
JOIN [dbo].[TextDocument] td ON sa.TextDocument_ID = td.TextDocument_ID
JOIN [dbo].[TopicAssignment] ta ON td.TextDocument_ID = ta.TextDocument_ID
WHERE ta.Topic_ID != -1
GROUP BY ta.Topic_ID, sa.Sentiment_Label
ORDER BY ta.Topic_ID, sa.Sentiment_Label

-- Distribuição de entidades por tipo
SELECT 
    Entity_Label,
    COUNT(*) as Total
FROM [dbo].[NamedEntity]
GROUP BY Entity_Label
ORDER BY Total DESC

-- Top 20 keywords mais frequentes
SELECT TOP 20
    Keyword_Text,
    COUNT(*) as Total
FROM [dbo].[Keyword]
GROUP BY Keyword_Text
ORDER BY Total DESC