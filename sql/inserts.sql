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