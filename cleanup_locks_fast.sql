-- Fast cleanup of IPFS lock errors using batched deletion
-- Run this in Azure Data Studio or sqlcmd for better performance

USE [rauditd]
GO

-- Show current count
SELECT COUNT(*) as 'Lock Error Records'
FROM [dbo].[TokenRecords]
WHERE [ipfs_error] LIKE '%repo.lock%'
GO

-- Batched deletion to avoid timeouts
DECLARE @BatchSize INT = 10000
DECLARE @TotalDeleted INT = 0
DECLARE @DeletedThisBatch INT

PRINT 'Starting batched deletion of lock error records...'

WHILE 1 = 1
BEGIN
    DELETE TOP (@BatchSize)
    FROM [dbo].[TokenRecords]
    WHERE [ipfs_error] LIKE '%repo.lock%'

    SET @DeletedThisBatch = @@ROWCOUNT
    SET @TotalDeleted = @TotalDeleted + @DeletedThisBatch

    IF @DeletedThisBatch = 0
        BREAK

    PRINT 'Deleted ' + CAST(@TotalDeleted AS VARCHAR(20)) + ' records so far...'

    -- Small delay to prevent overwhelming the system
    WAITFOR DELAY '00:00:00.100'
END

PRINT 'Cleanup complete! Total deleted: ' + CAST(@TotalDeleted AS VARCHAR(20)) + ' records'

-- Verify cleanup
SELECT COUNT(*) as 'Remaining Lock Error Records'
FROM [dbo].[TokenRecords]
WHERE [ipfs_error] LIKE '%repo.lock%'
GO

-- Show total remaining records
SELECT COUNT(*) as 'Total Records Remaining'
FROM [dbo].[TokenRecords]
GO