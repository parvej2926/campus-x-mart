export function mergeCommentList(existingComments = [], nextComments = []) {
  const seen = new Set();
  return [...(existingComments || []), ...(nextComments || [])].filter((comment) => {
    if (!comment || !comment.comment_id) return false;
    if (seen.has(comment.comment_id)) return false;
    seen.add(comment.comment_id);
    return true;
  });
}
