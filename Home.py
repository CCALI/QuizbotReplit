# Content remains the same until line 244
        # Centered Start Quiz button with custom styling
        col1, col2, col3 = st.columns([1, 2, 1])  # Changed from [2, 1, 2]
        with col2:
            if st.button("🚀 Start New Quiz", type="primary", key="start_quiz", use_container_width=True):
                start_new_quiz()
        
        st.markdown("---")
        
        # Show conversations
        conversations = db_ops.get_user_conversations(st.session_state.user_id)
        if conversations:
            st.subheader("Your Conversations")
            for conv in conversations:
                conv_id, title, context, start_time, end_time, status, msg_count, last_activity = conv
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])  # Changed from [3, 1, 1]
                    with col1:
                        st.write(f"**{title}**")
                        st.write(f"Messages: {msg_count} | Status: {status.title()}")
                    with col2:
                        if status == 'ongoing':
                            st.write("")  # Spacing
                            st.write("")  # Spacing
                            if st.button("▶️ Continue", key=f"continue_{conv_id}"):
                                continue_conversation(conv_id)
                    with col3:
                        st.write("")  # Spacing
                        st.write("")  # Spacing
                        if st.button("📋 View", key=f"view_{conv_id}"):
                            continue_conversation(conv_id)
                st.markdown("---")
        else:
            st.info("Start a new quiz to begin learning!")

if __name__ == "__main__":
    main()
