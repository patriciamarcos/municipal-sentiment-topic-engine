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