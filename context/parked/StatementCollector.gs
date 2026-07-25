/**
 * Automated Statement Collector
 * Runs daily to collect bank and credit card statements from Gmail and save them to Google Drive.
 */

// Configuration
const CONFIG = {
  SEARCH_QUERY: 'has:attachment filename:pdf from:(credit_cards@icici.bank.in OR estatement@icici.bank.in OR alerts@hdfcbank.net OR Statements@sbicard.com OR cc.statements@axis.bank.in) after:2025-12-31',
  FOLDER_NAME: 'Statement Scheduler',
  SHARED_FOLDER_ID: '1tdmsIw2Rj_TS1PZ9lSdIaN-rbcnsx9cd', // Optional: Put the Google Drive Folder ID here if running across multiple accounts
  LOG_SHEET_NAME: 'Statement Scheduler Logs',
  MAX_THREADS: 50 // Process up to 50 threads per run to avoid timeouts
};

// Main function to run the process
function processStatements() {
  const summary = {
    scanned: 0,
    found: 0,
    saved: 0,
    duplicates: 0,
    errors: []
  };

  try {
    const folder = getOrCreateFolder(CONFIG.FOLDER_NAME);
    const logSheet = getOrCreateLogSheet(folder, CONFIG.LOG_SHEET_NAME);
    const processedIds = getProcessedMessageIds(logSheet);
    
    // Search for emails
    const threads = GmailApp.search(CONFIG.SEARCH_QUERY, 0, CONFIG.MAX_THREADS);
    
    for (const thread of threads) {
      summary.scanned += thread.getMessageCount();
      const messages = thread.getMessages();
      
      for (const message of messages) {
        const messageId = message.getId();
        
        // Check if already processed
        if (processedIds.has(messageId)) {
          // Message already processed, skip
          continue;
        }

        const date = message.getDate();
        const sender = message.getFrom();
        const subject = message.getSubject();
        const attachments = message.getAttachments();
        
        let foundStatement = false;

        for (const attachment of attachments) {
          if (attachment.getContentType() === 'application/pdf' || attachment.getName().toLowerCase().endsWith('.pdf')) {
            summary.found++;
            foundStatement = true;

            const institutionInfo = identifyInstitution(sender, subject);
            const formattedDate = Utilities.formatDate(date, Session.getScriptTimeZone(), "yyyy-MM-dd");
            const newFilename = `${formattedDate}_${institutionInfo.bank}_${institutionInfo.type}.pdf`;
            
            try {
              // Save to Drive
              const blob = attachment.copyBlob().setName(newFilename);
              const file = folder.createFile(blob);
              
              summary.saved++;
              
              // Log Success
              logSheet.appendRow([
                new Date(),
                sender,
                institutionInfo.bank,
                institutionInfo.type,
                attachment.getName(),
                newFilename,
                file.getUrl(),
                'Saved',
                messageId
              ]);
            } catch (e) {
              summary.errors.push(`Failed to save ${newFilename}: ${e.toString()}`);
              // Log Error
              logSheet.appendRow([
                new Date(),
                sender,
                institutionInfo.bank,
                institutionInfo.type,
                attachment.getName(),
                newFilename,
                '',
                'Failed',
                messageId
              ]);
            }
          }
        }
        
        // If no PDF attachments found, we still log it so we don't process this email again
        if (!foundStatement) {
           logSheet.appendRow([
              new Date(),
              sender,
              '',
              '',
              '',
              '',
              '',
              'Ignored (No PDF)',
              messageId
            ]);
        }
      }
    }
    
    sendSummaryEmail(summary);
    
  } catch (globalError) {
    summary.errors.push(`Global Error: ${globalError.toString()}`);
    sendSummaryEmail(summary);
  }
}

// Helpers

function getOrCreateFolder(folderName) {
  if (CONFIG.SHARED_FOLDER_ID) {
    return DriveApp.getFolderById(CONFIG.SHARED_FOLDER_ID);
  }
  
  const folders = DriveApp.getFoldersByName(folderName);
  if (folders.hasNext()) {
    return folders.next();
  } else {
    return DriveApp.createFolder(folderName);
  }
}

function getOrCreateLogSheet(folder, sheetName) {
  const files = folder.getFilesByName(sheetName);
  let sheetFile;
  if (files.hasNext()) {
    sheetFile = files.next();
  } else {
    // Create new Google Sheet
    // Using DriveApp advanced service workaround to create a sheet
    // If Drive API v2/v3 is not enabled in Advanced Services, fallback to SpreadsheetApp
    const ss = SpreadsheetApp.create(sheetName);
    const tempFile = DriveApp.getFileById(ss.getId());
    tempFile.moveTo(folder);
    sheetFile = tempFile;
    
    // Add headers
    const sheet = ss.getSheets()[0];
    sheet.appendRow([
      'Process Date', 'Sender', 'Bank Name', 'Statement Type', 
      'Original Filename', 'Saved Filename', 'Drive Link', 'Status', 'Message ID'
    ]);
    sheet.setFrozenRows(1);
    sheet.getRange("A1:I1").setFontWeight("bold");
    return sheet;
  }
  
  return SpreadsheetApp.openById(sheetFile.getId()).getSheets()[0];
}

function getProcessedMessageIds(sheet) {
  const processedIds = new Set();
  const lastRow = sheet.getLastRow();
  
  if (lastRow > 1) {
    // Message ID is in column I (9)
    const data = sheet.getRange(2, 9, lastRow - 1, 1).getValues();
    for (const row of data) {
      if (row[0]) {
        processedIds.add(row[0].toString());
      }
    }
  }
  
  return processedIds;
}

function identifyInstitution(sender, subject) {
  let bank = 'UnknownBank';
  let type = 'Statement';
  
  const senderLower = sender.toLowerCase();
  const subjectLower = subject.toLowerCase();
  
  // Identify Bank
  if (senderLower.includes('hdfc')) bank = 'HDFC';
  else if (senderLower.includes('icici')) bank = 'ICICI';
  else if (senderLower.includes('sbi')) bank = 'SBI';
  else if (senderLower.includes('axis')) bank = 'Axis';
  else if (senderLower.includes('kotak')) bank = 'Kotak';
  else if (senderLower.includes('citi')) bank = 'Citi';
  else if (senderLower.includes('amex') || senderLower.includes('american express')) bank = 'Amex';
  else if (senderLower.includes('standard chartered') || senderLower.includes('sc.com')) bank = 'StanChart';
  
  // Identify Type
  if (subjectLower.includes('credit card') || senderLower.includes('cards') || subjectLower.includes('card')) {
    type = 'CreditCard';
  } else if (subjectLower.includes('account') || subjectLower.includes('bank statement') || subjectLower.includes('estatement')) {
    type = 'BankStatement';
  }
  
  return { bank: bank, type: type };
}

function sendSummaryEmail(summary) {
  const emailBody = `
Automated Statement Collector Summary:

Emails Scanned: ${summary.scanned}
Statements Found: ${summary.found}
New Files Saved: ${summary.saved}
Duplicates Skipped/Ignored: ${summary.scanned - summary.saved - summary.errors.length}

Errors Encountered: ${summary.errors.length}
${summary.errors.length > 0 ? '\nDetails:\n' + summary.errors.join('\n') : ''}
  `;
  
  GmailApp.sendEmail(
    Session.getActiveUser().getEmail(), 
    `Statement Collector Report - ${Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd")}`, 
    emailBody
  );
}
