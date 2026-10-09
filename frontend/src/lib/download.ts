/** Hands a file generated in the browser to the user (the browser's own download) */
export const saveFile = (content: Blob, fileName: string) => {
  const url = URL.createObjectURL(content);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  // Give the browser time to start the download before freeing the file
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
